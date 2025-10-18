#!/bin/bash
# Production deployment script for BecaTicker
# Run this script to deploy BecaTicker for production use

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

ACTUAL_USER=${SUDO_USER:-$(whoami)}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== BecaTicker Production Deployment ==="
echo "User: $ACTUAL_USER"
echo "Directory: $SCRIPT_DIR"
echo ""

# Create logs directory
echo "Creating logs directory..."
mkdir -p "$SCRIPT_DIR/logs"
chown $ACTUAL_USER:$ACTUAL_USER "$SCRIPT_DIR/logs"

# Create images directory if it doesn't exist
echo "Setting up images directory..."
mkdir -p "$SCRIPT_DIR/images"
chown $ACTUAL_USER:$ACTUAL_USER "$SCRIPT_DIR/images"

# Install system dependencies if needed
echo "Checking system dependencies..."
apt update
apt install -y python3 python3-pip python3-venv python3-dev git build-essential

# Set up Python virtual environment
echo "Setting up Python virtual environment..."
VENV_PATH="$SCRIPT_DIR/venv"
[ -d "$VENV_PATH" ] && rm -rf "$VENV_PATH"
sudo -u $ACTUAL_USER python3 -m venv "$VENV_PATH"

# Install Python packages
echo "Installing Python dependencies..."
sudo -u $ACTUAL_USER bash -c "
    source '$VENV_PATH/bin/activate'
    pip install --upgrade pip
    pip install -r '$SCRIPT_DIR/requirements.txt'
"

# Build RGB matrix library
echo "Building RGB matrix library..."
sudo -u $ACTUAL_USER bash -c "
    source '$VENV_PATH/bin/activate'
    cd '$SCRIPT_DIR/hzeller'
    make clean
    make build-python PYTHON='$VENV_PATH/bin/python'
    cd bindings/python
    '$VENV_PATH/bin/python' setup.py install
"

# Set up systemd service
echo "Installing systemd service..."
cp "$SCRIPT_DIR/becaticker.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable becaticker

# Set proper permissions
echo "Setting file permissions..."
chown -R $ACTUAL_USER:$ACTUAL_USER "$SCRIPT_DIR"
chmod +x "$SCRIPT_DIR/run.sh"
chmod +x "$SCRIPT_DIR/update.sh"

# Production security recommendations
echo ""
echo "=== Production Security Recommendations ==="
echo "1. Change default admin password via web interface"
echo "2. Configure firewall to restrict web interface access"
echo "3. Set up SSL/TLS for the web interface if needed"
echo "4. Review log files regularly in logs/ directory"
echo ""

echo "=== Deployment Complete! ==="
echo ""
echo "To start BecaTicker:"
echo "  sudo systemctl start becaticker"
echo ""
echo "To check status:"
echo "  sudo systemctl status becaticker"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u becaticker -f"
echo "  tail -f logs/becaticker.log"
echo ""
echo "Web interface will be available at:"
echo "  http://$(hostname -I | cut -d' ' -f1):5000"
echo ""
echo "Default login: admin / becaticker123 (CHANGE THIS!)"