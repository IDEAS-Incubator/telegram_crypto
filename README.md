# Telegram Tools

This project is designed to provide a platform for managing and processing Telegram group messages using Python and PM2.

## Features

- Download messages from Telegram groups or private chats.
- Filter messages by date range (`from_date` and `to_date`).
- Upload the messages as JSON files to an AWS S3 bucket.
- Health check endpoint for service monitoring.
- Secure and configurable using environment variables.

---

## Prerequisites

Ensure the following tools and packages are installed on your system:

- **Python**: Version 3.12 or higher.
- **Node.js**: Version 16 (LTS) or higher.
- **PM2**: Installed globally via npm.
- **Git**: Installed for cloning the repository.

---

## Setup Instructions

### Step 1: Update and Install Git

Run the following commands to ensure your system is updated and Git is installed:

```bash
sudo apt update
sudo apt install git
```

Verify the installation:

```bash
git --version
```

### Step 2: Clone the Repository

Clone the project repository:

```bash
git clone https://github.com/IDEAS-Incubator/telegram_crypto.git
```

Navigate to the project directory:

```bash
cd telegram_crypto/
```

### Step 3: Configure Environment Variables

Create and edit the `.env` file with the required environment variables:

```bash
nano .env
```

Add the necessary configuration, such as Telegram API credentials and AWS credentials.

### Step 4: Create a Python Virtual Environment

1. Install the `python3-venv` package if not already installed:
   ```bash
   sudo apt install python3.12-venv
   ```
2. Create the virtual environment:
   ```bash
   python3 -m venv env
   ```
3. Activate the virtual environment:
   ```bash
   source env/bin/activate
   ```

### Step 5: Install Dependencies

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

### Step 6: Run the Script

Run the Python script directly to test:

```bash
python api_time.py group_name.txt
```

---

## Using PM2 to Run the Script

### Step 1: Install Node.js and PM2

1. Install Node.js using NVM:
   ```bash
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
   source ~/.nvm/nvm.sh
   nvm install --lts
   nvm use --lts
   ```
2. Verify Node.js and npm versions:
   ```bash
   node -v
   npm -v
   ```
3. Install PM2 globally:
   ```bash
   npm install -g pm2
   ```

### Step 2: Run the Script Using PM2

Start the script with PM2:

```bash
pm2 start api_time.py --name telegram-api --interpreter python3 -- ./group_name.txt
```

### Step 3: Manage the Script with PM2

- **View the process list:**
  ```bash
  pm2 list
  ```
- **View logs:**
  ```bash
  pm2 logs telegram-api
  ```
- **Restart the script:**
  ```bash
  pm2 restart telegram-api
  ```
- **Stop the script:**
  ```bash
  pm2 stop telegram-api
  ```
- **Delete the script:**
  ```bash
  pm2 delete telegram-api
  ```

### Step 4: Persist PM2 Processes

Save the PM2 process list to ensure it restarts on system boot:

```bash
pm2 save
pm2 startup
```

Follow the instructions provided by PM2 to complete the setup.

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
python cmd.py file_path.txt --from_date YYYY-MM-DD --to_date YYYY-MM-DD
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

## Summary of Commands

```bash
# Update system and install Git
sudo apt update
sudo apt install git

# Clone the repository
git clone https://github.com/IDEAS-Incubator/telegram_crypto.git
cd telegram_crypto/

# Configure environment variables
nano .env

# Create and activate Python virtual environment
sudo apt install python3.12-venv
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt

# Test the script
python api_time.py group_name.txt

# Install Node.js and PM2
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.1/install.sh | bash
source ~/.nvm/nvm.sh
nvm install --lts
nvm use --lts
npm install -g pm2

# Run the script using PM2
pm2 start api_time.py --name telegram-api --interpreter python3 -- ./group_name.txt

# PM2 Management Commands
pm2 list
pm2 logs telegram-api
pm2 restart telegram-api
pm2 stop telegram-api
pm2 delete telegram-api
pm2 save
pm2 startup
```

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

## Notes

- Ensure the `.env` file is correctly configured before running the script.
- The AWS S3 bucket will be created automatically if it does not exist.
- For large chats, the API retrieves messages in batches to avoid memory issues.
- Use PM2 to keep the script running in the background and for easier process management.
- Activate the virtual environment whenever installing new dependencies or debugging locally.

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
