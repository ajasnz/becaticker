#!/bin/bash
# Test script for BecaTicker arcade mode

echo "Testing BecaTicker Arcade Mode..."
echo "==============================="

# Test 1: Check if arcade scripts exist
echo "1. Checking arcade scripts..."
if [ -f "arcade/start_arcade.sh" ]; then
    echo "   ✓ Production arcade script exists"
else
    echo "   ✗ Production arcade script missing"
fi

if [ -f "arcade/start_arcade_dev.sh" ]; then
    echo "   ✓ Development arcade script exists"
else
    echo "   ✗ Development arcade script missing"
fi

# Test 2: Check script permissions
echo ""
echo "2. Checking script permissions..."
for script in "arcade/start_arcade.sh" "arcade/start_arcade_dev.sh" "arcade/stop_arcade.sh" "arcade/stop_arcade_dev.sh"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "   ✓ $script is executable"
        else
            echo "   ⚠ $script exists but not executable - fixing..."
            chmod +x "$script"
        fi
    fi
done

# Test 3: Check ROM directory
echo ""
echo "3. Checking ROM directory..."
if [ -d "test_roms" ]; then
    echo "   ✓ test_roms directory exists"
    
    # Count ROMs
    mame_count=$(find test_roms/mame -name "*.zip" 2>/dev/null | wc -l)
    nes_count=$(find test_roms/nes -name "*.nes" 2>/dev/null | wc -l)
    
    echo "   - MAME ROMs: $mame_count"
    echo "   - NES ROMs: $nes_count"
    
    if [ $((mame_count + nes_count)) -gt 0 ]; then
        echo "   ✓ Test ROMs found"
    else
        echo "   ⚠ No test ROMs found - creating some..."
        mkdir -p test_roms/mame test_roms/nes
        echo "# Test MAME ROM" > test_roms/mame/test_game.zip
        echo "# Test NES ROM" > test_roms/nes/test_game.nes
        echo "   ✓ Test ROMs created"
    fi
else
    echo "   ⚠ test_roms directory missing - creating..."
    mkdir -p test_roms/mame test_roms/nes
    echo "# Test MAME ROM" > test_roms/mame/test_game.zip
    echo "# Test NES ROM" > test_roms/nes/test_game.nes
    echo "   ✓ test_roms directory and test files created"
fi

# Test 4: Run development arcade mode for a few seconds
echo ""
echo "4. Testing development arcade mode..."
echo "   Starting arcade mode for 10 seconds..."

# Start arcade mode in background
./arcade/start_arcade_dev.sh &
ARCADE_PID=$!

# Wait 10 seconds
sleep 10

# Stop arcade mode
kill $ARCADE_PID 2>/dev/null
wait $ARCADE_PID 2>/dev/null

echo "   ✓ Development arcade mode test completed"

# Test 5: Check configuration
echo ""
echo "5. Checking configuration..."
if [ -f "config.json" ]; then
    if grep -q "arcade_mode" config.json; then
        echo "   ✓ arcade_mode configuration found in config.json"
    else
        echo "   ⚠ arcade_mode configuration missing from config.json"
    fi
else
    echo "   ✗ config.json not found"
fi

echo ""
echo "==============================="
echo "Arcade mode test completed!"
echo ""
echo "To manually test arcade mode:"
echo "1. Run: ./arcade/start_arcade_dev.sh"
echo "2. Press Ctrl+C to stop"
echo ""
echo "For production mode (if RetroPie is installed):"
echo "1. Run: ./arcade/start_arcade.sh"
echo "2. Run: ./arcade/stop_arcade.sh"