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
cat > "$SCRIPT_DIR/arcade/start_arcade.sh" << EOF
#!/bin/bash
# Start arcade mode script for BecaTicker
# This script launches EmulationStation configured for the LED Matrix display

# Set up logging
LOG_FILE="/tmp/becaticker_arcade.log"
exec 1> >(tee -a "\$LOG_FILE")
exec 2>&1

echo "\$(date): Starting BecaTicker Arcade Mode..."

# Check if RetroPie is installed
if [ ! -d "/opt/retropie" ] && [ ! -d "/home/$ACTUAL_USER/RetroPie" ]; then
    echo "ERROR: RetroPie not found. Please install RetroPie first."
    exit 1
fi

# Set environment variables for LED Matrix display
export DISPLAY=:0
export XAUTHORITY="/home/$ACTUAL_USER/.Xauthority"

# RetroPie paths
RETROPIE_HOME="/home/$ACTUAL_USER/RetroPie"
EMULATIONSTATION_PATH="/opt/retropie/supplementary/emulationstation/emulationstation"
ES_SETTINGS_DIR="/opt/retropie/configs/all/emulationstation"

# Check if EmulationStation exists
if [ ! -f "\$EMULATIONSTATION_PATH" ]; then
    echo "ERROR: EmulationStation not found at \$EMULATIONSTATION_PATH"
    exit 1
fi

# Create ES settings directory if it doesn't exist
mkdir -p "\$ES_SETTINGS_DIR"

echo "Starting EmulationStation..."

# Start EmulationStation with minimal options
exec "\$EMULATIONSTATION_PATH" \\
    --resolution 128 128 \\
    --gamelist-only \\
    --no-splash \\
    --windowed \\
    --debug
EOF

cat > "$SCRIPT_DIR/arcade/stop_arcade.sh" << 'EOF'
#!/bin/bash
# Stop arcade mode script for BecaTicker
# This script stops EmulationStation and all related emulator processes

# Set up logging
LOG_FILE="/tmp/becaticker_arcade.log"
exec 1> >(tee -a "\$LOG_FILE")
exec 2>&1

echo "\$(date): Stopping BecaTicker Arcade Mode..."

# Function to kill processes by name
kill_process() {
    local process_name="\$1"
    local pids=\$(pgrep -f "\$process_name" 2>/dev/null)
    
    if [ -n "\$pids" ]; then
        echo "Stopping \$process_name processes: \$pids"
        # Try graceful termination first
        kill -TERM \$pids 2>/dev/null
        sleep 2
        
        # Force kill if still running
        local remaining=\$(pgrep -f "\$process_name" 2>/dev/null)
        if [ -n "\$remaining" ]; then
            echo "Force killing remaining \$process_name processes: \$remaining"
            kill -KILL \$remaining 2>/dev/null
        fi
    fi
}

# Stop all emulator and EmulationStation processes
kill_process "emulationstation"
kill_process "retroarch"
kill_process "runcommand"

echo "Arcade mode stopped successfully"
exit 0
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