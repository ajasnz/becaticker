#!/bin/bash
# Simple arcade mode stop script for BecaTicker - Development Version

# Set up logging
LOG_FILE="/tmp/becaticker_arcade.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "$(date): Stopping BecaTicker Arcade Mode (Development Version)..."

# Remove status file
ARCADE_STATUS_FILE="/tmp/becaticker_arcade_active"
rm -f "$ARCADE_STATUS_FILE"

# Kill the development arcade process
pkill -f "start_arcade_dev.sh" 2>/dev/null || true
pkill -f "becaticker_arcade" 2>/dev/null || true

echo "$(date): Arcade mode stopped successfully"
exit 0