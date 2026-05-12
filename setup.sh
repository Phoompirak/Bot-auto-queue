#!/usr/bin/env bash
set -e

echo "=== Installing system dependencies ==="
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv wget curl

echo "=== Installing Google Chrome ==="
wget -q -O /tmp/google-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt-get install -y /tmp/google-chrome.deb
rm /tmp/google-chrome.deb

echo "=== Setting up Python virtual environment ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Setup complete! ==="
echo "Next steps:"
echo "  1. Copy .env file:  cp .env.example .env  (then fill in your values)"
echo "  2. Install service:  sudo cp bot.service /etc/systemd/system/"
echo "  3. Enable service:   sudo systemctl enable bot"
echo "  4. Start service:    sudo systemctl start bot"
echo "  5. Check status:     sudo systemctl status bot"
