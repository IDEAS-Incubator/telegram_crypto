import argparse
import logging
import json
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import pytz
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import ChatInvalidError
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Telegram API credentials
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONENUMBER')

# AWS S3 credentials
AWS_REGION = os.getenv('AWS_REGION')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

# Global Telegram client with in-memory session
client = TelegramClient(StringSession(), API_ID, API_HASH)


def parse_date(date_string):
    """Parse date string to datetime object with UTC timezone."""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")


def create_s3_client():
    """Create an S3 client using credentials from .env."""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=AWS_REGION
    )


async def create_s3_bucket(bucket_name):
    """Create an S3 bucket if it doesn't exist."""
    s3_client = create_s3_client()
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket '{bucket_name}' already exists.")
    except ClientError:
        try:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
            )
            logger.info(f"Bucket '{bucket_name}' created successfully.")
        except Exception as e:
            logger.error(f"Failed to create bucket '{bucket_name}': {e}")
            raise


async def upload_file_to_s3(bucket_name, file_path, key):
    """Upload a file to an S3 bucket and return the HTTPS URL."""
    s3_client = create_s3_client()
    try:
        s3_client.upload_file(file_path, bucket_name, key)
        logger.info(f"File '{file_path}' uploaded to S3 bucket '{bucket_name}' as '{key}'.")
        region = os.getenv("AWS_REGION")
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{key}"
        return s3_url
    except Exception as e:
        logger.error(f"Failed to upload file to S3: {e}")
        raise


async def download_chat_messages(username, from_date=None, to_date=None):
    """Download messages from a Telegram chat with optional date filtering."""
    try:
        if not client.is_connected():
            await client.start(phone=PHONE_NUMBER)

        messages = []
        async for message in client.iter_messages(username, limit=None):
            if not message.date:
                continue

            message_date = message.date.astimezone(pytz.UTC).date()

            if from_date and message_date < from_date.date():
                continue
            if to_date and message_date > to_date.date():
                continue

            if message.text:
                messages.append({
                    "date": message.date.isoformat(),
                    "sender_id": message.sender_id,
                    "message": message.text,
                    "message_id": message.id
                })

        return messages
    except ChatInvalidError:
        logger.error(f"Chat '{username}' not found.")
        raise ValueError(f"Chat '{username}' not found or inaccessible.")
    except Exception as e:
        logger.error(f"Error downloading messages: {e}")
        raise


async def process_chats(file_path, from_date=None, to_date=None):
    """Process a file containing usernames, download messages, and upload to S3."""
    with open(file_path, 'r') as file:
        usernames = [line.strip() for line in file.readlines()]

    await create_s3_bucket(S3_BUCKET_NAME)
    for username in usernames:
        try:
            messages = await download_chat_messages(username, from_date, to_date)
            filename = f"telegram_{username}_{datetime.now().strftime('%Y_%m_%d')}.json"
            with open(filename, 'w') as f:
                json.dump(messages, f, indent=4)

            s3_url = await upload_file_to_s3(S3_BUCKET_NAME, filename, filename)
            logger.info(f"Messages for '{username}' uploaded to S3: {s3_url}")
        except Exception as e:
            logger.error(f"Failed to process '{username}': {e}")


def main():
    parser = argparse.ArgumentParser(description="Download Telegram messages and upload to S3.")
    parser.add_argument("file", help="Path to file containing Telegram usernames")
    parser.add_argument("--from_date", help="Start date for filtering messages (YYYY-MM-DD)")
    parser.add_argument("--to_date", help="End date for filtering messages (YYYY-MM-DD)")

    args = parser.parse_args()

    from_date = parse_date(args.from_date) if args.from_date else None
    to_date = parse_date(args.to_date) if args.to_date else None

    asyncio.run(process_chats(args.file, from_date, to_date))


if __name__ == "__main__":
    main()
