#!/bin/bash

# BecaTicker Setup - Simple LED matrix display setup

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

ACTUAL_USER=${SUDO_USER:-$(whoami)}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up BecaTicker..."

# Install system packages including cython3
apt update  
apt install -y python3 python3-pip python3-venv python3-dev git build-essential cython3

# Create virtual environment
VENV_PATH="$SCRIPT_DIR/venv"
[ -d "$VENV_PATH" ] && rm -rf "$VENV_PATH"
sudo -u $ACTUAL_USER python3 -m venv "$VENV_PATH"

# Install Python packages and build RGB library
sudo -u $ACTUAL_USER bash -c "
    source '$VENV_PATH/bin/activate'
    pip install --upgrade pip
    pip install flask icalendar pillow cython
    
    # Build RGB matrix library  
    cd '$SCRIPT_DIR/hzeller'
    make clean
    make build-python PYTHON='$VENV_PATH/bin/python'
    cd bindings/python
    '$VENV_PATH/bin/python' setup.py install
"

# Install systemd service
cat > /etc/systemd/system/becaticker.service << EOF
[Unit]
Description=BecaTicker LED Display
After=network.target

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$VENV_PATH/bin
ExecStart=$VENV_PATH/bin/python becaticker.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable becaticker

# Create default config if needed
[ ! -f config.json ] && sudo -u $ACTUAL_USER cat > config.json << 'EOF'
{
    "department_name": "Your Department",
    "messages": ["Welcome!", "Check calendar for events"],
    "calendar_urls": [],
    "matrix_options": {
        "rows": 64, "cols": 64, "chain_length": 4, "parallel": 2,
        "hardware_mapping": "adafruit-hat", "brightness": 60
    },
    "display_settings": {
        "scroll_speed": 2,
        "message_color": {"red": 255, "green": 255, "blue": 255},
        "department_color": {"red": 0, "green": 255, "blue": 255},
        "clock_color": {"red": 255, "green": 255, "blue": 255}
    }
}
EOF

sudo -u $ACTUAL_USER mkdir -p templates

echo "Setup complete!"
echo "Start with: sudo systemctl start becaticker"
echo "Web interface: http://$(hostname -I | cut -d' ' -f1):5000"