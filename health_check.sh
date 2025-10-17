#!/bin/bash
# BecaTicker Health Check Script
# Use this script to verify BecaTicker is running correctly

echo "=== BecaTicker Health Check ==="
echo ""

# Check if service is running
echo "1. Checking systemd service status..."
if systemctl is-active --quiet becaticker; then
    echo "   ✓ BecaTicker service is running"
else
    echo "   ✗ BecaTicker service is not running"
    echo "   Run: sudo systemctl start becaticker"
fi

# Check if web interface is responding
echo ""
echo "2. Checking web interface..."
if curl -s http://localhost:5000 > /dev/null; then
    echo "   ✓ Web interface is responding"
else
    echo "   ✗ Web interface is not responding"
    echo "   Check logs: sudo journalctl -u becaticker -n 20"
fi

# Check log files
echo ""
echo "3. Checking log files..."
if [ -f "logs/becaticker.log" ]; then
    echo "   ✓ Log file exists"
    echo "   Last 3 log entries:"
    tail -n 3 logs/becaticker.log | sed 's/^/     /'
else
    echo "   ✗ No log file found"
fi

# Check configuration
echo ""
echo "4. Checking configuration..."
if [ -f "config.json" ]; then
    echo "   ✓ Configuration file exists"
else
    echo "   ✗ Configuration file missing"
fi

# Check virtual environment
echo ""
echo "5. Checking virtual environment..."
if [ -d "venv" ]; then
    echo "   ✓ Virtual environment exists"
else
    echo "   ✗ Virtual environment missing"
    echo "   Run: sudo ./deploy.sh"
fi

echo ""
echo "=== Health Check Complete ==="