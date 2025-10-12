#!/bin/bash
# Stop arcade mode script for BecaTicker
# This script stops EmulationStation and all related emulator processes

# Set up logging
LOG_FILE="/tmp/becaticker_arcade.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "$(date): Stopping BecaTicker Arcade Mode..."

# Function to kill processes by name
kill_process() {
    local process_name="$1"
    local pids=$(pgrep -f "$process_name" 2>/dev/null)
    
    if [ -n "$pids" ]; then
        echo "Stopping $process_name processes: $pids"
        # Try graceful termination first
        kill -TERM $pids 2>/dev/null
        sleep 2
        
        # Force kill if still running
        local remaining=$(pgrep -f "$process_name" 2>/dev/null)
        if [ -n "$remaining" ]; then
            echo "Force killing remaining $process_name processes: $remaining"
            kill -KILL $remaining 2>/dev/null
        fi
    else
        echo "No $process_name processes found"
    fi
}

# Stop all emulator and EmulationStation processes
echo "Stopping emulators and EmulationStation..."

# Common emulator processes
EMULATOR_PROCESSES=(
    "emulationstation"
    "retroarch"
    "lr-"
    "mame"
    "stella"
    "mupen64plus"
    "pcsx"
    "ppsspp"
    "reicast"
    "vice"
    "dosbox"
    "scummvm"
    "advmame"
    "dgen"
    "gpsp"
    "jzintv"
    "linapple"
    "osmose"
    "pifba"
    "pisnes"
    "uae4arm"
    "xroar"
    "zdoom"
)

# Kill each emulator type
for emulator in "${EMULATOR_PROCESSES[@]}"; do
    kill_process "$emulator"
done

# Also kill any processes using the framebuffer
kill_process "fb1"

# Clean up any remaining arcade-related processes
pkill -f "arcade" 2>/dev/null || true
pkill -f "RetroPie" 2>/dev/null || true

# Reset framebuffer settings
export SDL_VIDEODRIVER=""
export SDL_FBDEV=""
export FRAMEBUFFER=""

echo "Arcade mode stopped successfully"

# Optional: Restore original display settings
if command -v fbset >/dev/null 2>&1; then
    fbset -fb /dev/fb0 -g 1920 1080 1920 1080 32 2>/dev/null || true
fi

exit 0