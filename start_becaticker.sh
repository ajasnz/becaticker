#!/bin/bash

# BecaTicker Startup Script
# This script provides a convenient way to start the BecaTicker application
# with proper environment setup and error handling.

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🎯 Starting BecaTicker LED Matrix Display System"
echo "================================================"

# Check if we're running as root (required for GPIO access)
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (for GPIO access)"
   echo "   Please run: sudo ./start_becaticker.sh"
   exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip in virtual environment
pip install --upgrade pip > /dev/null 2>&1

# Check if the RGB matrix library is compiled
if [ ! -f "hzeller/lib/librgbmatrix.a" ]; then
    echo "⚠️  RGB Matrix library not found. Attempting to compile..."
    cd hzeller
    make build-python PYTHON=$(which python3)
    cd ..
    echo "✅ RGB Matrix library compiled successfully"
fi

# Install Python dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies in virtual environment..."
    pip install -r requirements.txt
    pip install -r hzeller/bindings/python/requirements.txt 2>/dev/null || true
    echo "✅ Dependencies installed"
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Check if config.json exists, if not create a default one
if [ ! -f "config.json" ]; then
    echo "⚙️  Creating default configuration file..."
    cat > config.json << 'EOF'
{
  "department_name": "DEPARTMENT",
  "scrolling_messages": [
    "Welcome to our department!",
    "Have a great day!",
    "Check our website for updates"
  ],
  "calendar_urls": [],
  "web_port": 5000,
  "matrix_options": {
    "chain1": {
      "rows": 64,
      "cols": 64,
      "chain_length": 4,
      "parallel": 1,
      "brightness": 75,
      "gpio_mapping": "adafruit-hat"
    },
    "chain2": {
      "rows": 64,
      "cols": 64,
      "chain_length": 4,
      "parallel": 1,
      "brightness": 75,
      "gpio_mapping": "adafruit-hat"
    }
  },
  "display_settings": {
    "text_color": [255, 255, 255],
    "clock_color": [0, 255, 0],
    "background_color": [0, 0, 0],
    "scroll_speed": 0.05,
    "calendar_refresh_minutes": 30
  },
  "arcade_mode": {
    "enabled": true,
    "trigger_command": "/usr/bin/emulationstation"
  }
}
EOF
    echo "✅ Default configuration created"
fi

# Display system information
echo ""
echo "🔍 System Information:"
echo "   Python version: $(python3 --version)"
echo "   Working directory: $SCRIPT_DIR"
echo "   Configuration file: config.json"
echo "   Log files will be in: logs/"
echo ""

# Show network information for web interface access
echo "🌐 Web Interface Information:"
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "Unable to determine IP")
echo "   Local access: http://localhost:5000"
echo "   Network access: http://$LOCAL_IP:5000"
echo ""

# Trap to handle graceful shutdown
trap 'echo "🛑 Shutting down BecaTicker..."; kill $PYTHON_PID 2>/dev/null; exit 0' INT TERM

# Start the application
echo "🚀 Starting BecaTicker application..."
echo "   Press Ctrl+C to stop"
echo "   Logs will be displayed below:"
echo "================================================"
echo ""

# Start Python application with logging using virtual environment
sudo venv/bin/python becaticker.py --log-level INFO 2>&1 | tee -a "logs/becaticker_$(date +%Y%m%d_%H%M%S).log" &
PYTHON_PID=$!

# Wait for the Python process
wait $PYTHON_PID