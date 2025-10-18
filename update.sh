#!/bin/bash

# BecaTicker Auto-Update Script
# This script is called before service startup to update the code

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/logs/update.log"

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_message "Starting BecaTicker update process..."

cd "$SCRIPT_DIR"

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    log_message "Not a git repository, skipping update"
    exit 0
fi

# Check network connectivity
if ! ping -c 1 github.com >/dev/null 2>&1; then
    log_message "No network connectivity, skipping update"
    exit 0
fi

# Store current commit hash
CURRENT_COMMIT=$(git rev-parse HEAD)
log_message "Current commit: $CURRENT_COMMIT"

# Fetch latest changes
log_message "Fetching latest changes..."
if ! git fetch origin main 2>>"$LOG_FILE"; then
    log_message "Git fetch failed, continuing with existing code"
    exit 0
fi

# Check if there are updates available
LATEST_COMMIT=$(git rev-parse origin/main)
if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ]; then
    log_message "Already up to date"
    exit 0
fi

log_message "Updates available. Latest commit: $LATEST_COMMIT"

# Backup current config before update
if [ -f "config.json" ]; then
    cp config.json config.json.backup.$(date +%Y%m%d_%H%M%S)
    log_message "Backed up current configuration"
fi

# Attempt to pull updates
log_message "Pulling updates..."
if git pull origin main 2>>"$LOG_FILE"; then
    log_message "Successfully updated to latest version"
    
    # Update submodules if needed
    if [ -f ".gitmodules" ]; then
        log_message "Updating submodules..."
        git submodule update --init --recursive 2>>"$LOG_FILE" || log_message "Submodule update failed"
    fi
    
    # Check if requirements.txt changed and update dependencies
    if git diff --name-only HEAD~1 HEAD | grep -q "requirements.txt"; then
        log_message "Requirements changed, updating Python dependencies..."
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            pip install -r requirements.txt --upgrade 2>>"$LOG_FILE" || log_message "Dependency update failed"
        fi
    fi
    
    # Rebuild RGB matrix library if needed
    if git diff --name-only HEAD~1 HEAD | grep -q "hzeller/"; then
        log_message "RGB matrix library changed, rebuilding..."
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            cd hzeller
            make clean 2>>"$LOG_FILE" || true
            make build-python PYTHON="$SCRIPT_DIR/venv/bin/python" 2>>"$LOG_FILE" || log_message "RGB library build failed"
            cd bindings/python
            "$SCRIPT_DIR/venv/bin/python" setup.py install 2>>"$LOG_FILE" || log_message "RGB library install failed"
            cd "$SCRIPT_DIR"
        fi
    fi
    
else
    log_message "Git pull failed, attempting to resolve conflicts..."
    
    # Try to stash local changes and pull
    git stash push -m "Auto-backup before update $(date)" 2>>"$LOG_FILE" || true
    
    if git pull origin main 2>>"$LOG_FILE"; then
        log_message "Successfully updated after stashing local changes"
        log_message "Local changes have been stashed. Use 'git stash pop' to restore if needed."
    else
        log_message "Update failed, resetting to last known good state"
        git reset --hard "$CURRENT_COMMIT" 2>>"$LOG_FILE"
        exit 1
    fi
fi

# Restore config backup if the original was modified
if [ -f "config.json.backup.$(date +%Y%m%d)_"* ] && [ ! -f "config.json" ]; then
    LATEST_BACKUP=$(ls -t config.json.backup.* | head -n1)
    cp "$LATEST_BACKUP" config.json
    log_message "Restored configuration from backup"
fi

log_message "Update process completed successfully"