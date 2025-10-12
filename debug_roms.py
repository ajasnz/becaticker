#!/usr/bin/env python3
"""
Debug ROM scanning for BecaTicker arcade mode
"""

import os
import sys

# Add the current directory to Python path to import becaticker
sys.path.insert(0, '.')

# Import the necessary classes
from becaticker import Config, ArcadeManager
import logging

# Set up logging to see debug messages
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_rom_scanning():
    """Debug the ROM scanning process"""
    print("🔍 Debugging ROM Scanning Process")
    print("=" * 50)
    
    # Create config and arcade manager
    config = Config()
    arcade_manager = ArcadeManager(config)
    
    print(f"📁 ROM Directory: {arcade_manager.rom_directory}")
    print(f"📂 Directory exists: {os.path.exists(arcade_manager.rom_directory)}")
    
    if os.path.exists(arcade_manager.rom_directory):
        print("\n📋 Directory contents:")
        try:
            items = os.listdir(arcade_manager.rom_directory)
            for item in items:
                item_path = os.path.join(arcade_manager.rom_directory, item)
                if os.path.isdir(item_path):
                    print(f"  📁 {item}/")
                    try:
                        sub_items = os.listdir(item_path)
                        for sub_item in sub_items:
                            print(f"    📄 {sub_item}")
                    except Exception as e:
                        print(f"    ❌ Error reading {item}: {e}")
                else:
                    print(f"  📄 {item}")
        except Exception as e:
            print(f"  ❌ Error listing directory: {e}")
    else:
        print("  ❌ Directory does not exist")
    
    print("\n🔍 ROM Scanning Results:")
    roms = arcade_manager.get_available_roms()
    
    if roms:
        for system, rom_list in roms.items():
            print(f"  🎮 {system}: {len(rom_list)} ROMs")
            for rom in rom_list:
                print(f"    - {rom}")
    else:
        print("  ❌ No ROMs found")
    
    print(f"\n📊 Total ROMs: {sum(len(rom_list) for rom_list in roms.values())}")
    
    # Check configuration values
    print("\n⚙️ Configuration:")
    print(f"  ROM directory from config: {config.get('second_display.arcade_mode.rom_directory', 'NOT SET')}")
    print(f"  Arcade enabled: {config.get('second_display.arcade_mode.enabled', 'NOT SET')}")
    
    # Test file detection directly
    print("\n🧪 Direct File Detection Test:")
    test_files = [
        "test_roms/arcade/galaga.zip",
        "test_roms/arcade/pacman.zip", 
        "test_roms/nes/supermario.nes"
    ]
    
    for test_file in test_files:
        abs_path = os.path.abspath(test_file)
        exists = os.path.exists(test_file)
        print(f"  {'✅' if exists else '❌'} {test_file}")
        if exists:
            print(f"    📍 Absolute path: {abs_path}")
            print(f"    📏 Size: {os.path.getsize(test_file)} bytes")

def check_working_directory():
    """Check current working directory"""
    print("\n📍 Working Directory Info:")
    print(f"  Current working directory: {os.getcwd()}")
    print(f"  Script directory: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"  Python path: {sys.path[:3]}...")  # First 3 entries

if __name__ == "__main__":
    check_working_directory()
    debug_rom_scanning()