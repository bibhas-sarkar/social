#!/usr/bin/env bash
# ==============================================================================
# Matchday EPL - Autonomous Social Publishing Engine VPS Deployment Script
# ==============================================================================
set -e

# Color definitions
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}================================================================${NC}"
echo -e "${CYAN}   MATCHDAY EPL - AUTONOMOUS ENGINE VPS DEPLOYMENT${NC}"
echo -e "${CYAN}================================================================${NC}"

# 1. Load configuration from .env
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found in $SCRIPT_DIR${NC}"
    exit 1
fi

VPS_IP=$(grep -E "^VPS_IP=" .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')
VPS_KEY_RAW=$(grep -E "^VPS_KEY=" .env | cut -d '=' -f2- | tr -d '"' | tr -d "'" | tr -d '[:space:]')

if [ -z "$VPS_IP" ] || [ -z "$VPS_KEY_RAW" ]; then
    echo -e "${RED}Error: VPS_IP or VPS_KEY not configured in .env${NC}"
    exit 1
fi

# Expand tilde in key path
VPS_KEY="${VPS_KEY_RAW/#\~/$HOME}"

if [ ! -f "$VPS_KEY" ]; then
    echo -e "${RED}Error: SSH Private Key file not found at: $VPS_KEY${NC}"
    exit 1
fi

chmod 600 "$VPS_KEY"

REMOTE_USER="root"
REMOTE_DEST="/root/social"
SSH_CMD="ssh -i $VPS_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=15 $REMOTE_USER@$VPS_IP"

echo -e "Target VPS:       ${GREEN}$REMOTE_USER@$VPS_IP${NC}"
echo -e "SSH Key:          ${GREEN}$VPS_KEY${NC}"
echo -e "Remote Directory: ${GREEN}$REMOTE_DEST${NC}"
echo ""

# 2. Test SSH Connection
echo -e "${CYAN}▶ [1/6] Testing SSH connection to $VPS_IP...${NC}"
$SSH_CMD "echo 'Connected successfully to $(hostname)'"
echo -e "${GREEN}✓ SSH connectivity verified.${NC}\n"

# 3. Prepare Remote System Dependencies
echo -e "${CYAN}▶ [2/6] Ensuring remote Python 3, venv, and system packages are installed...${NC}"
$SSH_CMD "
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-venv rsync curl git
    mkdir -p $REMOTE_DEST
"
echo -e "${GREEN}✓ System packages prepared.${NC}\n"

# 4. Sync Project Files via rsync
echo -e "${CYAN}▶ [3/6] Syncing codebase to $REMOTE_DEST...${NC}"
rsync -avz --delete \
    -e "ssh -i $VPS_KEY -o StrictHostKeyChecking=no" \
    --exclude "venv" \
    --exclude ".git" \
    --exclude "__pycache__" \
    --exclude "*.pyc" \
    --exclude ".pytest_cache" \
    --exclude "cron.log" \
    "$SCRIPT_DIR/" "$REMOTE_USER@$VPS_IP:$REMOTE_DEST/"

# Copy .env explicitly
scp -i "$VPS_KEY" -o StrictHostKeyChecking=no "$SCRIPT_DIR/.env" "$REMOTE_USER@$VPS_IP:$REMOTE_DEST/.env"
echo -e "${GREEN}✓ Codebase & environment synced.${NC}\n"

# 5. Remote Virtual Environment & Playwright Setup
echo -e "${CYAN}▶ [4/6] Setting up Python virtual environment & Playwright dependencies...${NC}"
$SSH_CMD "
    cd $REMOTE_DEST
    if [ ! -d 'venv' ]; then
        python3 -m venv venv
    fi
    ./venv/bin/pip install --upgrade pip -q
    ./venv/bin/pip install -r requirements.txt -q
    ./venv/bin/playwright install chromium
    ./venv/bin/playwright install-deps chromium
"
echo -e "${GREEN}✓ Python dependencies & Playwright Chromium installed.${NC}\n"

# 6. Configure Systemd Service
echo -e "${CYAN}▶ [5/6] Creating & enabling systemd service (matchday-social.service)...${NC}"
$SSH_CMD "
cat << 'EOF' > /etc/systemd/system/matchday-social.service
[Unit]
Description=Matchday EPL Autonomous Social Publishing Daemon
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$REMOTE_DEST
ExecStart=$REMOTE_DEST/venv/bin/python main.py --channel matchday --daemon
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal
EnvironmentFile=$REMOTE_DEST/.env

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable matchday-social.service
    systemctl restart matchday-social.service
"
echo -e "${GREEN}✓ Systemd service configured and started.${NC}\n"

# 7. Verification & Service Status
echo -e "${CYAN}▶ [6/6] Verifying deployment and daemon status...${NC}"
$SSH_CMD "
    sleep 2
    systemctl status matchday-social.service --no-pager
"
echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}   DEPLOYMENT COMPLETED SUCCESSFULLY ON VPS ($VPS_IP)!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo -e "Useful VPS Commands:"
echo -e "  - View live daemon logs:   ${YELLOW}ssh -i $VPS_KEY root@$VPS_IP 'journalctl -u matchday-social.service -f'${NC}"
echo -e "  - Trigger manual slot:     ${YELLOW}ssh -i $VPS_KEY root@$VPS_IP 'cd /root/social && ./venv/bin/python main.py --channel matchday --slot 1'${NC}"
echo -e "  - Restart service:         ${YELLOW}ssh -i $VPS_KEY root@$VPS_IP 'systemctl restart matchday-social.service'${NC}"
echo -e "  - Stop service:            ${YELLOW}ssh -i $VPS_KEY root@$VPS_IP 'systemctl stop matchday-social.service'${NC}"
