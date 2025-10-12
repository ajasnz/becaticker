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

# Install system packages
apt update  
apt install -y python3 python3-pip python3-venv python3-dev git build-essential cython3 \
    lsb-release sudo xmlstarlet joystick jq dialog unzip

# Create virtual environment
VENV_PATH="$SCRIPT_DIR/venv"
[ -d "$VENV_PATH" ] && rm -rf "$VENV_PATH"
sudo -u $ACTUAL_USER python3 -m venv "$VENV_PATH"

# Install Python packages and build RGB library
sudo -u $ACTUAL_USER bash -c "
    source '$VENV_PATH/bin/activate'
    pip install --upgrade pip
    pip install flask icalendar pillow cython requests python-dateutil
    
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

# Install RetroPie for arcade mode
echo "Installing RetroPie for arcade mode..."
cd /opt
if [ ! -d "RetroPie-Setup" ]; then
    git clone --depth=1 https://github.com/RetroPie/RetroPie-Setup.git
    chown -R $ACTUAL_USER:$ACTUAL_USER RetroPie-Setup
fi

# Install RetroPie basic system (non-interactive)
sudo -u $ACTUAL_USER bash -c "
    cd /opt/RetroPie-Setup
    sudo __nodialog=1 ./retropie_packages.sh setup basic_install
"

# Create RetroPie configuration for LED matrix display
RETROPIE_CONFIG="/opt/retropie/configs/all/retroarch.cfg"
mkdir -p /opt/retropie/configs/all
cat >> "$RETROPIE_CONFIG" << 'EOF'
# LED Matrix Display Configuration for BecaTicker
video_driver = "sdl2"
video_fullscreen = "false"
video_windowed_fullscreen = "false"
video_fullscreen_x = "128"
video_fullscreen_y = "128"
video_force_aspect = "true"
video_aspect_ratio_auto = "false"
custom_viewport_width = "128"
custom_viewport_height = "128"
custom_viewport_x = "0"
custom_viewport_y = "0"
video_scale_integer = "true"
video_smooth = "false"
EOF

# Create arcade mode control scripts
mkdir -p "$SCRIPT_DIR/arcade"
cat > "$SCRIPT_DIR/arcade/start_arcade.sh" << 'EOF'
#!/bin/bash
# Start arcade mode - launches EmulationStation for the LED matrix
export DISPLAY=:0
cd /opt/retropie/supplementary/emulationstation
sudo -u $USER ./emulationstation --windowed --resolution 128 128
EOF

cat > "$SCRIPT_DIR/arcade/stop_arcade.sh" << 'EOF'
#!/bin/bash
# Stop arcade mode - kills all emulation processes
pkill -f emulationstation
pkill -f retroarch
pkill -f runcommand
EOF

chmod +x "$SCRIPT_DIR/arcade/start_arcade.sh"
chmod +x "$SCRIPT_DIR/arcade/stop_arcade.sh"
chown -R $ACTUAL_USER:$ACTUAL_USER "$SCRIPT_DIR/arcade"

# Create ROM directories
mkdir -p /home/$ACTUAL_USER/RetroPie/roms/arcade
mkdir -p /home/$ACTUAL_USER/RetroPie/roms/nes
mkdir -p /home/$ACTUAL_USER/RetroPie/roms/gameboy
chown -R $ACTUAL_USER:$ACTUAL_USER /home/$ACTUAL_USER/RetroPie

echo "Setup complete!"
echo "Start BecaTicker with: sudo systemctl start becaticker"
echo "Web interface: http://$(hostname -I | cut -d' ' -f1):5000"
echo "ROM directory: /home/$ACTUAL_USER/RetroPie/roms/"
echo "Upload ROMs to enable arcade mode!"