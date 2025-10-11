#!/usr/bin/env python3
"""
Test script for the second display functionality.
This script can be run on a development machine to verify the logic without actual hardware.
"""

import sys
import os
import json
from datetime import datetime

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))


def test_config_loading():
    """Test that the configuration loads with second display settings."""
    print("Testing configuration loading...")

    # Test loading config
    from becaticker import Config

    config = Config("config.json")

    # Check if second display configuration exists
    second_display = config.get("second_display", {})
    print(f"Second display config: {second_display}")

    assert second_display.get("enabled") == True, "Second display should be enabled"
    assert second_display.get("type") == "clock", "Second display should be clock type"
    assert second_display.get("layout") == "2x2", "Second display should be 2x2 layout"

    print("✓ Configuration test passed")


def test_clock_display_creation():
    """Test that the ClockDisplay class can be instantiated."""
    print("Testing ClockDisplay creation...")

    from becaticker import Config, ClockDisplay

    # Mock matrix class for testing
    class MockMatrix:
        def __init__(self):
            self.height = 128
            self.width = 320  # 5x64 for chain 1 + additional space

    config = Config("config.json")
    matrix = MockMatrix()

    # Create clock display
    clock_display = ClockDisplay(matrix, config, row_offset=64)

    assert clock_display.row_offset == 64, "Row offset should be 64 for chain 2"
    assert clock_display.width == 128, "Clock display width should be 128 (2x64)"
    assert clock_display.height == 128, "Clock display height should be 128 (2x64)"

    print("✓ ClockDisplay creation test passed")


def test_color_configuration():
    """Test that colors are properly loaded from configuration."""
    print("Testing color configuration...")

    from becaticker import Config, ClockDisplay

    class MockMatrix:
        def __init__(self):
            self.height = 128
            self.width = 320

    config = Config("config.json")
    matrix = MockMatrix()
    clock_display = ClockDisplay(matrix, config, row_offset=64)

    colors = clock_display._get_colors()

    # Check that all required colors exist
    required_colors = [
        "face",
        "hour_hand",
        "minute_hand",
        "second_hand",
        "numbers",
        "ticks",
        "digital",
        "date",
    ]
    for color_name in required_colors:
        assert color_name in colors, f"Color '{color_name}' should be defined"

    print("✓ Color configuration test passed")


def test_parallel_configuration():
    """Test that matrix options support parallel configuration."""
    print("Testing parallel configuration...")

    from becaticker import Config

    config = Config("config.json")
    matrix_options = config.get("matrix_options", {})

    assert matrix_options.get("parallel", 1) == 2, "Should have 2 parallel chains"
    assert matrix_options.get("chain_length", 1) == 5, "Chain 1 should have length 5"

    print("✓ Parallel configuration test passed")


def test_api_endpoints():
    """Test that the API endpoints are configured correctly."""
    print("Testing API endpoint configuration...")

    from becaticker import BecaTicker

    # Create a BecaTicker instance (this will create Flask app)
    ticker = BecaTicker()

    # Get the Flask app
    app = ticker.app

    # Check that our new endpoints are registered
    endpoints = [rule.rule for rule in app.url_map.iter_rules()]

    required_endpoints = ["/api/second-display", "/api/second-display/toggle"]

    for endpoint in required_endpoints:
        assert endpoint in endpoints, f"Endpoint '{endpoint}' should be registered"

    print("✓ API endpoint test passed")


def main():
    """Run all tests."""
    print("Running second display tests...\n")

    try:
        test_config_loading()
        test_clock_display_creation()
        test_color_configuration()
        test_parallel_configuration()
        test_api_endpoints()

        print("\n🎉 All tests passed! Second display implementation is ready.")
        print("\nTo use the second display:")
        print("1. Connect 4 panels in a 2x2 arrangement to chain 2")
        print("2. Start the application: python becaticker.py")
        print("3. Visit http://becaticker.local:5000 to configure")
        print("4. Use the new API endpoints:")
        print("   - GET /api/second-display - Get second display config")
        print("   - POST /api/second-display - Update second display config")
        print("   - POST /api/second-display/toggle - Toggle second display on/off")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
