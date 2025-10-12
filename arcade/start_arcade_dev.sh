#!/bin/bash
# Development version of start arcade mode script for BecaTicker
# This script provides a development/testing version without requiring full RetroPie setup

# Set up logging with proper permissions
LOG_FILE="/tmp/becaticker_arcade_dev.log"
# Ensure we can write to the log file
touch "$LOG_FILE" 2>/dev/null || LOG_FILE="./arcade_dev.log"

exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "$(date): Starting BecaTicker Arcade Mode (Development Version)..."

# Development paths
DEV_ROM_DIR="./test_roms"
BECATICKER_DIR="."

# Create test ROM directories
mkdir -p "$DEV_ROM_DIR/mame"
mkdir -p "$DEV_ROM_DIR/nes"

# Create some test ROM files if they don't exist
if [ ! -f "$DEV_ROM_DIR/mame/test_game.zip" ]; then
    echo "Creating test ROM files..."
    echo "# Test MAME ROM - Pac-Man Clone" > "$DEV_ROM_DIR/mame/test_game.zip"
    echo "# Test NES ROM - Super Mario Clone" > "$DEV_ROM_DIR/nes/test_game.nes"
    echo "# Another test ROM - Street Fighter Clone" > "$DEV_ROM_DIR/mame/another_game.zip"
fi

# Function to scan for ROMs
scan_roms() {
    local rom_count=0
    local system_count=0
    
    echo "Scanning for ROMs in development mode..."
    
    # Check each system directory
    for system_dir in "$DEV_ROM_DIR"/*; do
        if [ -d "$system_dir" ]; then
            local system_name=$(basename "$system_dir")
            local files=$(find "$system_dir" -name "*.zip" -o -name "*.nes" -o -name "*.rom" | wc -l)
            
            if [ "$files" -gt 0 ]; then
                echo "Found $files ROMs in $system_name system"
                # List the ROM files found
                find "$system_dir" -name "*.zip" -o -name "*.nes" -o -name "*.rom" | while read rom_file; do
                    local rom_name=$(basename "$rom_file")
                    echo "  - $rom_name"
                done
                rom_count=$((rom_count + files))
                system_count=$((system_count + 1))
            fi
        fi
    done
    
    echo "ROM scan complete: $rom_count ROMs in $system_count systems"
    return $rom_count
}

# Main development arcade function
start_dev_arcade() {
    echo "Starting development arcade interface..."
    
    # Scan for ROMs
    scan_roms
    local rom_count=$?
    
    # Create development arcade status
    echo "DEV_ARCADE_MODE_ACTIVE" > /tmp/becaticker_arcade_dev_status
    echo "$(date)" >> /tmp/becaticker_arcade_dev_status
    echo "ROM_COUNT=$rom_count" >> /tmp/becaticker_arcade_dev_status
    
    # Set up signal handlers for clean shutdown
    trap 'echo ""; echo "Received shutdown signal..."; cleanup_and_exit' SIGTERM SIGINT
    
    if [ $rom_count -gt 0 ]; then
        echo "=== DEVELOPMENT ARCADE MODE ==="
        echo "This is a development version of arcade mode"
        echo "Found $rom_count ROMs available for testing"
        echo "Systems available:"
        for system_dir in "$DEV_ROM_DIR"/*; do
            if [ -d "$system_dir" ]; then
                local system_name=$(basename "$system_dir")
                local count=$(find "$system_dir" -name "*.zip" -o -name "*.nes" -o -name "*.rom" | wc -l)
                if [ $count -gt 0 ]; then
                    echo "  - $system_name: $count games"
                fi
            fi
        done
        echo "Press Ctrl+C to stop"
        echo ""
        
        # Simulate arcade interface
        local counter=0
        while true; do
            counter=$((counter + 1))
            case $((counter % 4)) in
                1) echo "🕹️  Arcade Menu: Select Game System" ;;
                2) echo "🎮 MAME System Selected - $(find "$DEV_ROM_DIR/mame" -name "*.zip" 2>/dev/null | wc -l) games" ;;
                3) echo "🏆 NES System Selected - $(find "$DEV_ROM_DIR/nes" -name "*.nes" 2>/dev/null | wc -l) games" ;;
                0) echo "⚡ Arcade Mode Active - $(date '+%H:%M:%S')" ;;
            esac
            
            sleep 3
        done
    else
        echo "=== DEVELOPMENT ARCADE MODE (NO ROMS) ==="
        echo "No ROMs found - running in demo mode"
        echo "This demonstrates the arcade mode structure"
        echo "Add ROM files to $DEV_ROM_DIR to test with games"
        echo "Press Ctrl+C to stop"
        echo ""
        
        # Demo mode
        local counter=0
        while true; do
            counter=$((counter + 1))
            case $((counter % 3)) in
                1) echo "📺 Demo Mode: No ROMs Available" ;;
                2) echo "💿 Add .zip files to $DEV_ROM_DIR/mame/" ;;
                0) echo "🎯 Add .nes files to $DEV_ROM_DIR/nes/" ;;
            esac
            
            sleep 4
        done
    fi
}

# Cleanup function
cleanup_and_exit() {
    echo ""
    echo "Cleaning up development arcade mode..."
    rm -f /tmp/becaticker_arcade_dev_status
    echo "Development arcade mode finished successfully"
    exit 0
}

# Execute development arcade mode
echo "Initializing development arcade mode..."
start_dev_arcade