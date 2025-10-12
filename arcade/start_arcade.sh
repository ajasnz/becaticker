#!/bin/bash
# Start arcade mode script for BecaTicker
# This script starts a custom arcade interface for the LED Matrix display

# Set up logging with proper permissions
LOG_FILE="/tmp/becaticker_arcade.log"
# Create log file with proper permissions
sudo touch "$LOG_FILE"
sudo chown becaticker:becaticker "$LOG_FILE"
sudo chmod 664 "$LOG_FILE"

exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "$(date): Starting BecaTicker Arcade Mode..."

# Configuration
ARCADE_DIR="/home/becaticker/becaticker/arcade"
ROM_DIR="/home/becaticker/becaticker/test_roms"
BECATICKER_DIR="/home/becaticker/becaticker"

# Create ROM directory if it doesn't exist
mkdir -p "$ROM_DIR/mame"
mkdir -p "$ROM_DIR/nes"

# Function to scan for ROMs
scan_roms() {
    local rom_count=0
    local system_count=0
    
    echo "Scanning for ROMs..."
    
    # Check each system directory
    for system_dir in "$ROM_DIR"/*; do
        if [ -d "$system_dir" ]; then
            local system_name=$(basename "$system_dir")
            local files=$(find "$system_dir" -name "*.zip" -o -name "*.nes" -o -name "*.rom" | wc -l)
            
            if [ "$files" -gt 0 ]; then
                echo "Found $files ROMs in $system_name system"
                rom_count=$((rom_count + files))
                system_count=$((system_count + 1))
            fi
        fi
    done
    
    echo "ROM scan complete: $rom_count ROMs in $system_count systems"
    return $rom_count
}

# Function to start simple arcade interface
start_arcade_interface() {
    echo "Starting custom arcade interface for LED matrix..."
    
    # Kill any existing BecaTicker processes to avoid conflicts
    pkill -f "python.*becaticker.py" 2>/dev/null || true
    sleep 2
    
    # Start the BecaTicker with arcade mode
    cd "$BECATICKER_DIR"
    
    # Create a simple arcade status file
    echo "ARCADE_MODE_ACTIVE" > /tmp/becaticker_arcade_status
    echo "$(date)" >> /tmp/becaticker_arcade_status
    
    # Run ROM scan
    scan_roms
    local rom_count=$?
    
    if [ $rom_count -gt 0 ]; then
        echo "Starting arcade mode with $rom_count ROMs available"
        
        # Create arcade mode configuration
        cat > /tmp/arcade_config.json << EOF
{
    "arcade_mode": {
        "enabled": true,
        "rom_directory": "$ROM_DIR",
        "display_resolution": "128x128",
        "show_rom_count": true,
        "auto_return_timeout": 300
    }
}
EOF
        
        # Start Python arcade interface (this will integrate with the LED matrix)
        echo "Launching arcade interface..."
        python3 -c "
import sys
sys.path.append('$BECATICKER_DIR')
import json
import time
from becaticker import BecaTicker

# Load arcade configuration
with open('/tmp/arcade_config.json', 'r') as f:
    config = json.load(f)

print('Arcade Mode Started')
print('ROMs: $rom_count games available')
print('Press Ctrl+C to return to normal mode')

# Simple arcade loop - this would integrate with your LED matrix display
try:
    while True:
        # This is where you'd display the arcade interface on the LED matrix
        # For now, just show that arcade mode is running
        time.sleep(5)
        print(f'Arcade mode running... {time.strftime(\"%H:%M:%S\")}')
except KeyboardInterrupt:
    print('Arcade mode stopped')
    # Clean up
    import os
    os.remove('/tmp/becaticker_arcade_status')
"
        
    else
        echo "No ROMs found - creating demo mode"
        echo "Arcade mode running in demo mode (no ROMs available)"
        
        # Demo mode - just show arcade is active
        python3 -c "
import time
print('Arcade Demo Mode - No ROMs found')
print('Add ROM files to $ROM_DIR to enable games')
print('Press Ctrl+C to exit')

try:
    while True:
        time.sleep(5)
        print(f'Demo mode running... {time.strftime(\"%H:%M:%S\")}')
except KeyboardInterrupt:
    print('Arcade demo mode stopped')
    import os
    if os.path.exists('/tmp/becaticker_arcade_status'):
        os.remove('/tmp/becaticker_arcade_status')
"
    fi
}

# Main execution
echo "Initializing arcade mode..."

# Check if BecaTicker Python script exists
if [ ! -f "$BECATICKER_DIR/becaticker.py" ]; then
    echo "ERROR: BecaTicker script not found at $BECATICKER_DIR/becaticker.py"
    exit 1
fi

# Start the arcade interface
start_arcade_interface