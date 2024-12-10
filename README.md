# Telegram Message Downloader and S3 Uploader

This project provides an API and command-line tool to download messages from Telegram chats and upload them to an AWS S3 bucket. It supports filtering messages by date and uploading them as JSON files to S3.

---

## Features

- Download messages from Telegram groups or private chats.
- Filter messages by date range (`from_date` and `to_date`).
- Upload the messages as JSON files to an AWS S3 bucket.
- Health check endpoint for service monitoring.
- Secure and configurable using environment variables.

---

## Installation

1. Clone the repository:

   ```bash
   git clone <repository_url>
   cd <repository_name>
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables in a `.env` file. See [Environment Variables](#environment-variables) for details.

4. Run the API or command-line tool:
   - **API**: Start the FastAPI service:
     ```bash
        python api.py
     ```
   - **Command-line**: Process chats:
     ```bash
     python main.py file_path.txt --from_date YYYY-MM-DD --to_date YYYY-MM-DD
     ```

---

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Telegram API credentials
API_ID=<your_telegram_api_id>
API_HASH=<your_telegram_api_hash>
PHONENUMBER=<your_telegram_phone_number>

# AWS S3 credentials
AWS_ACCESS_KEY_ID=<your_aws_access_key_id>
AWS_SECRET_ACCESS_KEY=<your_aws_secret_access_key>
AWS_REGION=<your_aws_region>
S3_BUCKET_NAME=<your_s3_bucket_name>
```

Replace the placeholders with your actual values.

---

## API Endpoints

### 1. Health Check

**GET** `/health`

- **Response:**
  ```json
  {
    "status": "healthy",
    "service": "Telegram Message Downloader"
  }
  ```

### 2. Process Messages

**POST** `/process-messages/`

- **Parameters:**

  - `file`: A file containing a list of usernames (one per line).
  - `from_date` (optional): Start date for filtering messages (YYYY-MM-DD).
  - `to_date` (optional): End date for filtering messages (YYYY-MM-DD).

- **Response:**
  ```json
  {
    "summary": [
      {
        "username": "example_username",
        "status": "success",
        "message_count": 100,
        "s3_file": "https://bucket_name.s3.region.amazonaws.com/filename.json"
      },
      {
        "username": "another_username",
        "status": "failed",
        "error": "Chat 'another_username' not found or inaccessible."
      }
    ]
  }
  ```

---

## Command-Line Tool

### Usage

```bash
python main.py file_path.txt --from_date YYYY-MM-DD --to_date YYYY-MM-DD
```

### Arguments:

- `file`: Path to the file containing Telegram usernames.
- `--from_date`: (Optional) Start date for filtering messages.
- `--to_date`: (Optional) End date for filtering messages.

---

## How It Works

1. **Telegram API Integration**: Uses the `telethon` library to connect to Telegram and retrieve messages.
2. **Date Filtering**: Filters messages by date range if specified.
3. **AWS S3 Upload**: Saves messages as JSON files and uploads them to an S3 bucket.
4. **Error Handling**: Handles errors gracefully, such as invalid chats or missing credentials.

---

## Notes

- Ensure your `.env` file is correctly set up before running the application.
- The AWS S3 bucket will be created automatically if it does not exist.
- For large chats, the API retrieves messages in batches to avoid memory issues.

---

## Dependencies

- `fastapi`
- `uvicorn`
- `telethon`
- `boto3`
- `python-dotenv`

Install all dependencies using:

```bash
pip install -r requirements.txt
```

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
