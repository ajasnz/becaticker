#!/usr/bin/env python3
"""
Test script to verify arcade mode ROM detection and basic functionality.
"""

import sys
import os

# Add the current directory to Python path so we can import from becaticker.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from becaticker import Config, ArcadeManager

    def test_arcade_mode():
        """Test basic arcade mode functionality."""
        print("🎮 Testing Arcade Mode Functionality")
        print("=" * 40)

        # Initialize config and arcade manager
        config = Config()
        arcade_manager = ArcadeManager(config)

        print(f"📁 ROM Directory: {arcade_manager.rom_directory}")
        print(
            f"🔍 ROM Directory Exists: {os.path.exists(arcade_manager.rom_directory)}"
        )

        # Test RetroPie detection
        retropie_installed = arcade_manager.is_retropie_installed()
        print(f"🎮 RetroPie Installed: {retropie_installed}")

        # Test ROM scanning
        print("\n📦 Scanning for ROMs...")
        roms = arcade_manager.get_available_roms()

        if roms:
            total_roms = sum(len(rom_list) for rom_list in roms.values())
            print(f"✅ Found {total_roms} ROMs in {len(roms)} systems:")

            for system, rom_list in roms.items():
                print(f"  📁 {system}: {len(rom_list)} ROMs")
                for rom in rom_list[:3]:  # Show first 3 ROMs
                    print(f"    - {rom}")
                if len(rom_list) > 3:
                    print(f"    ... and {len(rom_list) - 3} more")
        else:
            print("❌ No ROMs found")

        # Test arcade status
        print("\n📊 Arcade Status Check...")
        status = arcade_manager.check_status()
        print(f"  Active: {status.get('active', False)}")
        print(f"  RetroPie Installed: {status.get('retropie_installed', False)}")
        print(f"  ROMs Available: {status.get('roms_available', 0)}")
        print(f"  Enabled: {status.get('enabled', False)}")

        # Check arcade scripts
        print("\n🔧 Checking Arcade Scripts...")
        script_dir = os.path.join(os.path.dirname(__file__), "arcade")
        start_script = os.path.join(script_dir, "start_arcade.sh")
        stop_script = os.path.join(script_dir, "stop_arcade.sh")

        print(f"  📁 Arcade Directory: {script_dir}")
        print(f"  📄 Start Script Exists: {os.path.exists(start_script)}")
        print(f"  📄 Stop Script Exists: {os.path.exists(stop_script)}")

        if os.path.exists(start_script):
            print(f"  ✅ Start Script Executable: {os.access(start_script, os.X_OK)}")
        if os.path.exists(stop_script):
            print(f"  ✅ Stop Script Executable: {os.access(stop_script, os.X_OK)}")

        # Overall assessment
        print("\n🎯 Assessment:")
        can_start = retropie_installed and bool(roms) and os.path.exists(start_script)
        print(f"  Can Start Arcade Mode: {'✅ YES' if can_start else '❌ NO'}")

        if not can_start:
            print("\n💡 Issues to fix:")
            if not retropie_installed:
                print("  - RetroPie not detected (run setup.sh or add test ROMs)")
            if not roms:
                print("  - No ROMs found (add ROM files to ROM directory)")
            if not os.path.exists(start_script):
                print("  - Arcade scripts missing (run setup.sh)")

        return can_start

    if __name__ == "__main__":
        success = test_arcade_mode()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure you're running this from the BecaTicker directory")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
