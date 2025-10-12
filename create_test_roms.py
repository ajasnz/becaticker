#!/usr/bin/env python3
"""
Create test ROM structure for BecaTicker arcade mode testing.
This creates dummy ROM files to test the arcade mode functionality.
"""

import os


def create_test_roms():
    """Create test ROM files and directory structure."""

    # ROM directory (matches the config)
    rom_base = "/home/pi/RetroPie/roms"

    # For local development, use a local directory
    if not os.path.exists("/home/pi/"):
        rom_base = "test_roms"

    systems = {
        "arcade": ["pacman.zip", "galaga.zip", "donkeykong.zip"],
        "nes": ["supermario.nes", "zelda.nes", "megaman.nes"],
        "gameboy": ["tetris.gb", "pokemon.gb", "zelda.gb"],
        "snes": ["supermario.sfc", "zelda.smc", "metroid.sfc"],
    }

    print(f"Creating test ROM structure in: {rom_base}")

    total_files = 0
    for system, roms in systems.items():
        system_dir = os.path.join(rom_base, system)
        os.makedirs(system_dir, exist_ok=True)
        print(f"  📁 Created directory: {system_dir}")

        for rom in roms:
            rom_path = os.path.join(system_dir, rom)
            with open(rom_path, "w") as f:
                f.write(f"# Test ROM file for {rom}\n")
                f.write(f"# This is a placeholder for testing arcade mode\n")
                f.write(f"# Replace with actual ROM files\n")
            print(f"    📄 Created test ROM: {rom}")
            total_files += 1

    print(f"\n✅ Created {total_files} test ROM files in {len(systems)} systems")
    print(f"📍 ROM directory: {rom_base}")

    # Create a README
    readme_path = os.path.join(rom_base, "README.txt")
    with open(readme_path, "w") as f:
        f.write("BecaTicker Test ROM Directory\n")
        f.write("=" * 30 + "\n\n")
        f.write(
            "These are test/placeholder ROM files created for testing arcade mode.\n"
        )
        f.write("Replace these files with actual ROM files to enable gameplay.\n\n")
        f.write("Supported file formats:\n")
        f.write("- .zip (MAME/Arcade)\n")
        f.write("- .nes (Nintendo Entertainment System)\n")
        f.write("- .gb/.gbc (Game Boy/Game Boy Color)\n")
        f.write("- .smc/.sfc (Super Nintendo)\n")
        f.write("- .bin/.rom (Various systems)\n\n")
        f.write("Note: You must provide your own legally-obtained ROM files.\n")

    print(f"📝 Created README: {readme_path}")

    return rom_base


if __name__ == "__main__":
    create_test_roms()
