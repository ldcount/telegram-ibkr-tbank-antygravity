# 🚀 COMPREHENSIVE SOP: ZERO-FUSS AUTOMATED DEPLOYMENT
**Author**: DevOps Architect PhD
**Date**: February 13, 2026
**Scope**: Full automation from VS Code push to VPS live update.

---

## 1. SERVER PREPARATION (AS ROOT)
Before automation can begin, the "Clean Slate" environment must be established.

### 1.1 Create the Dedicated Deploy User
Avoid using `root` or legacy users like `ghost` [cite: user's text]. 
```bash
# Create user manually (bypassing missing logger utility)
useradd -m -s /bin/bash deploy
passwd deploy
usermod -aG sudo deploy
```

### 1.2 Establish the Application Root
Standardize where bots live [cite: user's text].
```bash
mkdir -p /opt/bots
chown -R deploy:deploy /opt/bots
chmod -R 755 /opt/bots
```

### 1.3 Configure Sudo Privileges (The Automation Key)
GitHub must restart the service without a password prompt.
1. Run `visudo`.
2. Add this exact line at the very bottom:
```text
deploy ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart volatility_bot.service
```

---

## 2. SSH SECURITY & GITHUB HANDSHAKE

### 2.1 Generate Keys for the Deploy User
Switch to the new user: `su - deploy`.
```bash
ssh-keygen -t ed25519 -C "vps-deploy-key"
# Press ENTER for all prompts (No passphrase)
```

### 2.2 Authorize the Key on VPS
```bash
mkdir -p ~/.ssh
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

### 2.3 Add to GitHub Settings
1. Copy the **Public Key** (`cat ~/.ssh/id_ed25519.pub`).
2. Go to GitHub -> Profile -> **Settings** -> **SSH and GPG keys** -> **New SSH Key**.
3. Paste the key. This allows the VPS to "pull" from GitHub.

---

## 3. INITIAL REPOSITORY CLONE (THE "FIRST BOOT")
As the `deploy` user, verify connectivity and set up the folder.

### 3.1 Install Git
```bash
sudo apt update && sudo apt install git -y
```

### 3.2 Clone and Verify
```bash
cd /opt/bots
# Use the SSH URL (git@github.com:...)
git clone git@github.com:YOUR_USERNAME/Volatility-Bot.git volatility_bot
cd volatility_bot

# Verify connection to GitHub
git pull origin master
```

### 3.3 Set Up Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3.4 Create the Secret Environment File
```bash
nano .env
# Paste your TELEGRAM_TOKEN_PROD and other secrets here.
```

---

## 4. SYSTEMD SERVICE CONFIGURATION
Create the service file to keep the bot alive.

1. Create the file: `sudo nano /etc/systemd/system/volatility_bot.service`
2. Paste the following:
```ini
[Unit]
Description=Crypto Volatility Bot Service
After=network.target

[Service]
User=deploy
Group=deploy
WorkingDirectory=/opt/bots/volatility_bot
Environment="PYTHONUNBUFFERED=1"
ExecStart=/opt/bots/volatility_bot/venv/bin/python /opt/bots/volatility_bot/volatility_bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```
3. Enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable volatility_bot.service
sudo systemctl start volatility_bot.service
```

---

## 5. GITHUB ACTIONS SETUP (THE LIAISON)

### 5.1 Repository Secrets
Go to **Settings -> Security -> Secrets and variables -> Actions**. Add:
* `SSH_PRIVATE_KEY`: Content of `cat /home/deploy/.ssh/id_ed25519`.
* `REMOTE_HOST`: VPS IP Address.
* `REMOTE_USER`: `deploy`.
* `SSH_PORT`: Your custom Putty/SSH port [cite: user's text].

### 5.2 Create Workflow File
In your local IDE, create `.github/workflows/deploy.yml`:
```yaml
name: Continuous Deployment

on:
  push:
    branches: [ master ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.REMOTE_HOST }}
          username: ${{ secrets.REMOTE_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          port: ${{ secrets.SSH_PORT }}
          script: |
            cd /opt/bots/volatility_bot
            
            # Critical Ownership Fix for Root/Deploy conflict
            git config --global --add safe.directory /opt/bots/volatility_bot
            
            # Sync Files
            git fetch origin master
            git reset --hard origin/master
            
            # Update Environment
            ./venv/bin/pip install -r requirements.txt
            
            # Restart Service
            sudo systemctl restart volatility_bot.service
            systemctl is-active volatility_bot.service
```

---

## 6. CAVEATS & TROUBLESHOOTING
* **Git Status Block**: If `git status` fails with "dubious ownership," use the `safe.directory` config [cite: image_5e4191.png].
* **Port Connection**: If getting "i/o timeout," ensure Port SSH is open in both your VPS Provider Dashboard and server UFW [cite: user's text].
* **No File Changes**: If code doesn't update, run `git reset --hard origin/master` on the VPS to overwrite manual server edits.
