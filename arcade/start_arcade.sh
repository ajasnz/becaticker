#!/bin/bash
# Start arcade mode script for BecaTicker
# This script launches EmulationStation configured for the LED Matrix display

# Set up logging
LOG_FILE="/tmp/becaticker_arcade.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "$(date): Starting BecaTicker Arcade Mode..."

# Check if RetroPie is installed
if [ ! -d "/opt/retropie" ] && [ ! -d "/home/becaticker/RetroPie" ]; then
    echo "ERROR: RetroPie not found. Please install RetroPie first."
    exit 1
fi

# Set environment variables for LED Matrix display
export DISPLAY=:0
export XAUTHORITY="/home/becaticker/.Xauthority"

# RetroPie paths (using becaticker user)
RETROPIE_HOME="/home/becaticker/RetroPie"
EMULATIONSTATION_PATH="/opt/retropie/supplementary/emulationstation/emulationstation"
ES_SETTINGS_DIR="/opt/retropie/configs/all/emulationstation"

# Check if EmulationStation exists
if [ ! -f "$EMULATIONSTATION_PATH" ]; then
    echo "ERROR: EmulationStation not found at $EMULATIONSTATION_PATH"
    exit 1
fi

# Create ES settings directory if it doesn't exist
mkdir -p "$ES_SETTINGS_DIR"

# Configure EmulationStation for LED Matrix (low resolution mode)
ES_CONFIG="$ES_SETTINGS_DIR/es_settings.cfg"
cat > "$ES_CONFIG" << EOF
<?xml version="1.0"?>
<config>
    <bool name="BackgroundJoystickInput" value="false" />
    <bool name="DrawFramerate" value="false" />
    <bool name="EnableSounds" value="false" />
    <bool name="MoveCarousel" value="true" />
    <bool name="ParseGamelistOnly" value="false" />
    <bool name="QuickSystemSelect" value="true" />
    <bool name="ScrapeRatings" value="true" />
    <bool name="ScreenSaverControls" value="true" />
    <bool name="ShowHelpPrompts" value="false" />
    <bool name="SortAllSystems" value="false" />
    <bool name="SplashScreen" value="false" />
    <bool name="SplashScreenProgress" value="false" />
    <bool name="StartupSystem" value="" />
    <bool name="UseOSK" value="false" />
    <bool name="VidOmxPlayer" value="false" />
    <int name="MaxVRAM" value="100" />
    <int name="ScraperResizeHeight" value="0" />
    <int name="ScraperResizeWidth" value="0" />
    <int name="ScreenSaverTime" value="300000" />
    <string name="CollectionSystemsAuto" value="" />
    <string name="CollectionSystemsCustom" value="" />
    <string name="GamelistViewStyle" value="basic" />
    <string name="Scraper" value="screenscraper" />
    <string name="ScreenSaverBehavior" value="dim" />
    <string name="ThemeSet" value="carbon" />
    <string name="TransitionStyle" value="fade" />
    <string name="UIMode" value="Full" />
    <string name="UIMode_passkey" value="uuddlrlrba" />
</config>
EOF

echo "EmulationStation configuration created"

# Kill any existing EmulationStation instances
pkill -f emulationstation 2>/dev/null || true

# Wait a moment for cleanup
sleep 2

# Check for available framebuffers and configure SDL
if [ -c "/dev/fb1" ]; then
    export FRAMEBUFFER="/dev/fb1"
    export SDL_VIDEODRIVER=fbcon
    export SDL_FBDEV=/dev/fb1
    echo "Using framebuffer /dev/fb1 for LED matrix"
elif [ -c "/dev/fb0" ]; then
    export FRAMEBUFFER="/dev/fb0"
    export SDL_VIDEODRIVER=fbcon
    export SDL_FBDEV=/dev/fb0
    echo "Using framebuffer /dev/fb0 as fallback"
else
    # No framebuffer available, try X11 or dummy driver
    echo "No framebuffer devices found, trying alternative display methods"
    if [ -n "$DISPLAY" ]; then
        export SDL_VIDEODRIVER=x11
        echo "Using X11 display driver"
    else
        export SDL_VIDEODRIVER=dummy
        echo "WARNING: Using dummy video driver - no display output"
    fi
fi

echo "Starting EmulationStation..."

# Try different EmulationStation startup approaches
echo "Attempting to start EmulationStation with LED matrix configuration..."

# First attempt: Try with minimal configuration for LED matrix
if "$EMULATIONSTATION_PATH" --resolution 128 128 --gamelist-only --no-splash --windowed --debug 2>&1 | tee -a "$LOG_FILE"; then
    echo "EmulationStation started successfully"
else
    echo "First attempt failed, trying alternative configuration..."
    
    # Second attempt: Try with different video driver
    export SDL_VIDEODRIVER=software
    if "$EMULATIONSTATION_PATH" --resolution 128 128 --no-splash --debug 2>&1 | tee -a "$LOG_FILE"; then
        echo "EmulationStation started with software renderer"
    else
        echo "Second attempt failed, trying basic configuration..."
        
        # Third attempt: Try basic configuration
        export SDL_VIDEODRIVER=dummy
        if "$EMULATIONSTATION_PATH" --no-splash --debug 2>&1 | tee -a "$LOG_FILE"; then
            echo "EmulationStation started with dummy driver (no display)"
        else
            echo "ERROR: All EmulationStation startup attempts failed"
            echo "Check log file: $LOG_FILE"
            exit 1
        fi
    fi
fi