import argparse
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from telethon import TelegramClient
from telethon.errors import ChatInvalidError
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
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

# Argument parser for username file path
parser = argparse.ArgumentParser(description="Telegram Message Downloader Service")
parser.add_argument(
    "username_file", type=str, help="Path to the file containing usernames or group names."
)
args = parser.parse_args()

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

# Function to parse dates
def parse_date(date_string: str):
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Use YYYY-MM-DD."
        )

# Create S3 client
def create_s3_client():
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=AWS_REGION
    )

# Async function to process messages
async def process_messages_daily():
    """
    Download messages from Telegram and upload to S3 for the previous day.
    Scheduled to run daily at 00:01 AM Pacific Time.
    """
    logger.info("Running scheduled task to process messages.")

    try:
        # Calculate date range for the previous day in Pacific Time
        pacific = pytz.timezone("US/Pacific")
        now = datetime.now(pacific)
        from_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        to_date = from_date  # Same day for start and end of range

        # Read usernames from the file
        with open(args.username_file, "r") as file:
            usernames = [line.strip() for line in file.readlines()]

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
                    from_date=parse_date(from_date),
                    to_date=parse_date(to_date)
                )
                
                # Save messages to JSON file
                filename = f"telegram_{username.strip()}_{datetime.now().strftime('%Y_%m_%d')}.json"
                async with aiofiles.open(filename, mode='w') as f:
                    await f.write(json.dumps(result, indent=4))

                # Upload JSON file to S3
                s3_key = filename
                s3_url = await upload_file_to_s3(bucket_name, filename, s3_key)

                # Append success response
                result_summary.append({
                    "username": username.strip(),
                    "status": "success",
                    "message_count": result["message_count"],
                    "s3_file": s3_url
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
        
        logger.info(f"Daily processing completed. Summary: {result_summary}")
    except Exception as e:
        logger.error(f"Error in scheduled task: {e}")


# APScheduler setup
scheduler = BackgroundScheduler()

# Schedule the task to run daily at 00:01 AM Pacific Time
pacific_time_trigger = CronTrigger(
    hour=0, minute=1, timezone="US/Pacific"
)
scheduler.add_job(process_messages_daily, pacific_time_trigger)
scheduler.start()

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
    Disconnect Telegram client and shutdown scheduler on application shutdown.
    """
    try:
        if client.is_connected():
            await client.disconnect()
            logger.info("Telegram client disconnected.")
        scheduler.shutdown()
        logger.info("Scheduler shutdown.")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
