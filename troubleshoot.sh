s#!/bin/bash

# BecaTicker Troubleshooting Script
# This script helps diagnose common issues with the BecaTicker setup

echo "🔍 BecaTicker Troubleshooting"
echo "============================="
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "📍 Working Directory: $SCRIPT_DIR"
echo ""

# Check Python installation
echo "🐍 Python Environment Check:"
echo "   Python3: $(which python3 || echo 'NOT FOUND')"
echo "   Python3 version: $(python3 --version 2>/dev/null || echo 'NOT AVAILABLE')"
echo "   Virtual env exists: $([ -d "venv" ] && echo 'YES' || echo 'NO')"

if [ -d "venv" ]; then
    echo "   Virtual env python: $(ls -la venv/bin/python* 2>/dev/null || echo 'NOT FOUND')"
    echo "   Virtual env packages: $(venv/bin/pip list 2>/dev/null | wc -l || echo 'ERROR') packages installed"
fi
echo ""

# Check Git and submodules
echo "🔗 Git Repository Check:"
echo "   Git status: $(git status --porcelain 2>/dev/null && echo 'Clean' || echo 'Issues detected')"
echo "   Submodules: $(git submodule status 2>/dev/null | wc -l) submodules"
echo "   hzeller directory: $([ -d "hzeller" ] && echo 'EXISTS' || echo 'MISSING')"
echo ""

# Check RGB Matrix library
echo "🔨 RGB Matrix Library Check:"
echo "   Library file: $([ -f "hzeller/lib/librgbmatrix.a" ] && echo 'EXISTS' || echo 'MISSING')"
echo "   Python bindings: $([ -f "hzeller/bindings/python/rgbmatrix.so" ] && echo 'EXISTS' || echo 'MISSING')"
echo "   Cython source: $([ -f "hzeller/bindings/python/rgbmatrix/core.pyx" ] && echo 'EXISTS' || echo 'MISSING')"
echo "   Cython compiled: $([ -f "hzeller/bindings/python/rgbmatrix/core.cpp" ] && echo 'EXISTS' || echo 'MISSING')"
echo "   Python import test: $(python3 -c "import rgbmatrix" 2>/dev/null && echo 'SUCCESS' || echo 'FAILED')"
echo ""

# Check configuration files
echo "⚙️  Configuration Check:"
echo "   config.json: $([ -f "config.json" ] && echo 'EXISTS' || echo 'MISSING')"
echo "   requirements.txt: $([ -f "requirements.txt" ] && echo 'EXISTS' || echo 'MISSING')"
echo "   Service file: $([ -f "/etc/systemd/system/becaticker.service" ] && echo 'INSTALLED' || echo 'NOT INSTALLED')"
echo ""

# Check system service
echo "🔄 System Service Check:"
if systemctl is-enabled becaticker.service >/dev/null 2>&1; then
    echo "   Service enabled: YES"
    echo "   Service status: $(systemctl is-active becaticker.service)"
    echo "   Service errors: $(journalctl -u becaticker.service --no-pager -n 3 2>/dev/null | tail -1 || echo 'None recent')"
else
    echo "   Service enabled: NO"
fi
echo ""

# Check network and ports
echo "🌐 Network Check:"
LOCAL_IP=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "Unknown")
echo "   Local IP: $LOCAL_IP"
echo "   Port 5000 in use: $(netstat -tlnp 2>/dev/null | grep ':5000' >/dev/null && echo 'YES' || echo 'NO')"
echo ""

# Check hardware-related settings
echo "🔌 Hardware Configuration:"
if [ -f "/boot/firmware/config.txt" ]; then
    CONFIG_FILE="/boot/firmware/config.txt"
elif [ -f "/boot/config.txt" ]; then
    CONFIG_FILE="/boot/config.txt"
else
    CONFIG_FILE="NOT FOUND"
fi

echo "   Config file: $CONFIG_FILE"
if [ "$CONFIG_FILE" != "NOT FOUND" ]; then
    echo "   Audio disabled: $(grep -q 'dtparam=audio=off' "$CONFIG_FILE" && echo 'YES' || echo 'NO')"
    echo "   w1-gpio disabled: $(grep -q '#dtoverlay=w1-gpio' "$CONFIG_FILE" && echo 'YES' || echo 'NO')"
fi
echo ""

# Check file permissions
echo "📋 File Permissions:"
echo "   becaticker.py executable: $([ -x "becaticker.py" ] && echo 'YES' || echo 'NO')"
echo "   start_becaticker.sh executable: $([ -x "start_becaticker.sh" ] && echo 'YES' || echo 'NO')"
echo "   setup.sh executable: $([ -x "setup.sh" ] && echo 'YES' || echo 'NO')"
echo ""

# Suggest fixes
echo "🔧 Suggested Actions:"

if [ ! -d "venv" ]; then
    echo "   • Create virtual environment: python3 -m venv venv"
fi

if [ ! -f "hzeller/lib/librgbmatrix.a" ]; then
    echo "   • Build RGB matrix library: ./build_rgb_matrix.sh"
fi

if [ ! -f "hzeller/bindings/python/rgbmatrix/core.cpp" ]; then
    echo "   • Missing Cython compiled file. Install Cython: pip install Cython"
    echo "   • Then run: ./build_rgb_matrix.sh"
fi

if ! python3 -c "import rgbmatrix" 2>/dev/null; then
    echo "   • Python bindings not working. Try: ./build_rgb_matrix.sh"
fi

if [ ! -f "/etc/systemd/system/becaticker.service" ]; then
    echo "   • Install service: sudo cp becaticker.service /etc/systemd/system/"
fi

if ! systemctl is-enabled becaticker.service >/dev/null 2>&1; then
    echo "   • Enable service: sudo systemctl enable becaticker.service"
fi

echo ""
echo "📚 For more help, check README.md or run:"
echo "   sudo ./start_becaticker.sh  # Manual start"
echo "   sudo journalctl -u becaticker.service -f  # View service logs"
echo ""