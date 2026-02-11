# Deployment Guide: Telegram Bot to VPS

This guide walks you through deploying your Telegram bot to a generic Linux VPS (e.g., Ubuntu/Debian).

## Prerequisites

- A **VPS server** running Ubuntu 20.04/22.04 or Debian 11/12.
- **SSH access** to the server (IP address, username, password/key).
- Basic familiarity with the terminal.

---

## Step 1: Prepare the VPS

Connect to your VPS:
```bash
ssh root@your_vps_ip
# or if you have a specific user
ssh username@your_vps_ip
```

Update the system and install necessary packages:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git -y
```

---

## Step 2: Transfer Application Files

You have two main options to get your code onto the server.

### Option A: Using `scp` (Secure Copy) from your local machine
This is the simplest method if you don't use Git/GitHub extensively. It copies your local folder directly to the server.

1.  **On your local Windows machine**, open a terminal (PowerShell or Command Prompt).
2.  Run the following command (replace with your actual paths/IP):

```powershell
# Syntax: scp -r <local_path> <user>@<remote_ip>:<remote_path>
scp -r "c:\Users\dmitr\OneDrive\Desktop\Coding Python\telegram-ibkr-tbank-antygravity" root@your_vps_ip:/root/telegram-bot
```

### Option B: Using Git (Recommended)
If your code is on GitHub/GitLab:

1.  **On the VPS**:
    ```bash
    git clone https://github.com/yourusername/your-repo.git telegram-bot
    ```

---

## Step 3: Set Up the Environment

1.  **Navigate to the project directory** on the VPS:
    ```bash
    cd ~/telegram-bot
    # Note: If you used scp, the folder name might be 'telegram-ibkr-tbank-antygravity' unless you renamed it.
    # Adjust accordingly.
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    ```

3.  **Activate the virtual environment**:
    ```bash
    source venv/bin/activate
    ```

4.  **Install dependencies**:
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

---

## Step 4: Configure Environment Variables

1.  Create the `.env` file:
    ```bash
    nano .env
    ```

2.  Paste your environment variables. You can copy them from your local `.env` file.
    Example:
    ```ini
    TELEGRAM_TOKEN=your_token_here
    TELEGRAM_CHAT_ID=your_chat_id
    # Add other keys from your config.py
    ```

3.  Save and exit:
    - Press `Ctrl+O` then `Enter` to save.
    - Press `Ctrl+X` to exit.

---

## Step 5: Test the Bot Manually

Before setting up the background service, ensure the bot runs correctly.

```bash
# Make sure venv is active
python3 -m app.main
```

If it starts and logs "Bot started..." (or similar), press `Ctrl+C` to stop it. If there are errors, fix them before proceeding.

---

## Step 6: Set Up Systemd Service (Auto-Start)

This step ensures your bot runs in the background and restarts automatically if the server reboots or the bot crashes.

1.  **Create a service file**:
    ```bash
    sudo nano /etc/systemd/system/telegram-bot.service
    ```

2.  **Paste the following configuration**:
    *Adjust the paths (`/root/telegram-bot`) and user (`root`) if they are different.*

    ```ini
    [Unit]
    Description=Telegram Bot Service
    After=network.target

    [Service]
    # user running the bot (e.g., root, ubuntu, etc.)
    User=root
    # Group=root

    # Directory where your code is located
    WorkingDirectory=/root/telegram-bot

    # path to python in env AND path to main.py
    ExecStart=/root/telegram-bot/venv/bin/python3 -m app.main

    # Restart automatically if it crashes
    Restart=always
    RestartSec=10

    # Environment variables (optional, better to use .env file)
    # EnvironmentFile=/root/telegram-bot/.env

    [Install]
    WantedBy=multi-user.target
    ```

3.  **Reload systemd and start the service**:
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable telegram-bot
    sudo systemctl start telegram-bot
    ```

---

## Step 7: Manage and Monitor

-   **Check Status**:
    ```bash
    sudo systemctl status telegram-bot
    ```

-   **View Logs** (Real-time):
    ```bash
    sudo journalctl -u telegram-bot -f
    ```

-   **Stop the Bot**:
    ```bash
    sudo systemctl stop telegram-bot
    ```

-   **Restart the Bot** (e.g., after updating code):
    ```bash
    sudo systemctl restart telegram-bot
    ```

## Troubleshooting

-   **"Module not found"**: Ensure you installed requirements inside the virtual environment (`source venv/bin/activate`).
-   **"Permission denied"**: Check if `chmod +x` is needed (usually not for python files), or check ownership of files (`chown -R user:user folder`).
-   **Logs**: `journalctl` is your best friend. It shows everything the bot prints to stdout/stderr.
