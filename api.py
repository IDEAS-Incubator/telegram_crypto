from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from telethon import TelegramClient
from telethon.errors import ChatInvalidError
from dotenv import load_dotenv
from datetime import datetime
import pytz
import os
import logging
import json
import aiofiles
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# API configuration
app = FastAPI(
    title="Telegram Message Downloader",
    description="API to download messages from Telegram chats and upload them to S3",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telegram API credentials
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONENUMBER')

# AWS S3 credentials
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

# Global Telegram client
client = TelegramClient('session_name', API_ID, API_HASH)

def parse_date(date_string: str):
    """
    Parse date string to datetime object with UTC timezone
    
    Args:
        date_string (str): Date in YYYY-MM-DD format
    
    Returns:
        datetime: Parsed datetime object with UTC timezone
    
    Raises:
        HTTPException: If date format is invalid
    """
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Use YYYY-MM-DD."
        )

def create_s3_client():
    """Create an S3 client using credentials from .env."""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=AWS_REGION
    )

async def create_s3_bucket(bucket_name: str):
    """
    Create an S3 bucket if it doesn't exist.
    
    Args:
        bucket_name (str): Name of the S3 bucket.
    """
    s3_client = create_s3_client()
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket '{bucket_name}' already exists.")
    except ClientError:
        # Bucket doesn't exist, create it
        try:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
            logger.info(f"Bucket '{bucket_name}' created successfully.")
        except Exception as e:
            logger.error(f"Failed to create bucket '{bucket_name}': {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create bucket '{bucket_name}': {str(e)}"
            )

async def upload_file_to_s3(bucket_name: str, file_path: str, key: str) -> str:
    """
    Upload a file to an S3 bucket and return the HTTPS URL.
    
    Args:
        bucket_name (str): Name of the S3 bucket.
        file_path (str): Local file path to upload.
        key (str): Key name for the file in S3.

    Returns:
        str: The HTTPS URL of the uploaded file.
    """
    s3_client = create_s3_client()
    try:
        s3_client.upload_file(file_path, bucket_name, key)
        logger.info(f"File '{file_path}' uploaded to S3 bucket '{bucket_name}' as '{key}'.")
        # Generate the HTTPS URL
        region = os.getenv("AWS_REGION")
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
        return s3_url
    except Exception as e:
        logger.error(f"Failed to upload file to S3: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload file to S3: {str(e)}"
        )


async def download_chat_messages(
    username: str,
    token_name: str,
    from_date: datetime = None,
    to_date: datetime = None
):
    """
    Download messages from a Telegram chat, with optional filtering by date range.

    Args:
        username (str): Chat username or ID.
        token_name (str): Token name for the group/chat.
        from_date (datetime, optional): Start date for filtering messages.
        to_date (datetime, optional): End date for filtering messages.

    Returns:
        dict: Dictionary containing token_name, message_count, and the list of messages.
    """
    try:
        # Ensure the client is connected
        if not client.is_connected():
            await client.start(phone=PHONE_NUMBER)

        messages = []

        async for message in client.iter_messages(username, limit=None):  # No hard limit on iteration
            if not message.date:
                continue  # Skip messages without a valid date

            # Convert message date to UTC
            message_date = message.date.astimezone(pytz.UTC).date()

            # Apply date filtering
            if from_date and message_date < from_date.date():
                continue
            if to_date and message_date > to_date.date():
                continue

            # Add the message to the list
            if message.text:
                messages.append({
                    "date": message.date.isoformat(),
                    "sender_id": message.sender_id,
                    "message": message.text,
                    "message_id": message.id
                })

        # Return the messages and metadata
        return {
            "token_name": token_name,
            "message_count": len(messages),
            "messages": messages
        }

    except ChatInvalidError:
        logger.error(f"Chat not found: {username}")
        raise HTTPException(
            status_code=404,
            detail=f"Chat '{username}' not found or inaccessible."
        )
    except Exception as e:
        logger.error(f"Error downloading messages: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error downloading messages: {str(e)}"
        )


@app.post("/process-messages/")
async def process_messages_file(
    file: UploadFile = File(...),
    from_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(None, description="End date (YYYY-MM-DD)")
):
    """
    Process a file containing group/usernames and save messages to JSON files, then upload to S3.

    Parameters:
    - file: File containing list of usernames or group names.
    - from_date: Optional start date for filtering.
    - to_date: Optional end date for filtering.

    Returns:
    JSON response summarizing the processing status.
    """
    try:
        # Parse date filters
        from_date_obj = parse_date(from_date) if from_date else None
        to_date_obj = parse_date(to_date) if to_date else None

        # Read group/usernames from uploaded file
        content = await file.read()
        usernames = content.decode('utf-8').splitlines()

        result_summary = []
        bucket_name = S3_BUCKET_NAME

        # Ensure the S3 bucket exists
        await create_s3_bucket(bucket_name)
        
        for username in usernames:
            token_name = f"Token_{username.strip()}"
            try:
                # Download messages
                result = await download_chat_messages(
                    username=username.strip(),
                    token_name=token_name,
                    from_date=from_date_obj,
                    to_date=to_date_obj
                )
                
                # Save messages to JSON file
                filename = f"telegram_{username.strip()}_{datetime.now().strftime('%Y_%m_%d')}.json"
                async with aiofiles.open(filename, mode='w') as f:
                    await f.write(json.dumps(result, indent=4))

                # Upload JSON file to S3
                region = os.getenv("AWS_REGION")
                s3_key = filename  # Use filename as the S3 object key
                s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
                await upload_file_to_s3(bucket_name, filename, s3_key)

                # Append success response
                result_summary.append({
                    "username": username.strip(),
                    "status": "success",
                    "message_count": result["message_count"],
                    "s3_file": s3_url  # Include HTTPS URL
                })
            except HTTPException as e:
                # Append failure response for HTTP exceptions
                result_summary.append({
                    "username": username.strip(),
                    "status": "failed",
                    "error": e.detail
                })
            except Exception as e:
                # Append failure response for other exceptions
                result_summary.append({
                    "username": username.strip(),
                    "status": "failed",
                    "error": str(e)
                })
        
        return {"summary": result_summary}
    
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    """
    return {
        "status": "healthy", 
        "service": "Telegram Message Downloader"
    }

@app.on_event("shutdown")
async def shutdown_event():
    """
    Disconnect Telegram client on application shutdown.
    """
    try:
        if client.is_connected():
            await client.disconnect()
            logger.info("Telegram client disconnected.")
    except Exception as e:
        logger.error(f"Error during client disconnection: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
