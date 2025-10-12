#!/usr/bin/env python3
"""
Arcade Mode Diagnostic Script for BecaTicker
This script helps diagnose issues with arcade mode functionality.
"""

import os
import subprocess
import sys


def check_retropie_installation():
    """Check if RetroPie is installed."""
    print("🔍 Checking RetroPie Installation...")

    retropie_dirs = ["/opt/RetroPie-Setup", "/opt/retropie", "/home/pi/RetroPie"]
    found_dirs = []

    for directory in retropie_dirs:
        if os.path.exists(directory):
            found_dirs.append(directory)
            print(f"  ✅ Found: {directory}")
        else:
            print(f"  ❌ Not found: {directory}")

    if found_dirs:
        print(f"  ✅ RetroPie installation detected")
        return True
    else:
        print(f"  ❌ RetroPie not found")
        return False


def check_emulationstation():
    """Check if EmulationStation is available."""
    print("\n🔍 Checking EmulationStation...")

    es_paths = [
        "/opt/retropie/supplementary/emulationstation/emulationstation",
        "/usr/bin/emulationstation",
        "/usr/local/bin/emulationstation",
    ]

    for path in es_paths:
        if os.path.exists(path):
            print(f"  ✅ Found EmulationStation: {path}")
            try:
                # Check if it's executable
                result = subprocess.run(
                    [path, "--help"], capture_output=True, text=True, timeout=5
                )
                print(f"  ✅ EmulationStation is executable")
                return True
            except Exception as e:
                print(f"  ⚠️  EmulationStation found but not executable: {e}")
        else:
            print(f"  ❌ Not found: {path}")

    print(f"  ❌ EmulationStation not found or not executable")
    return False


def check_roms():
    """Check for available ROMs."""
    print("\n🔍 Checking ROM directories...")

    rom_base_dirs = [
        "/home/pi/RetroPie/roms",
        "/opt/retropie/configs/all/emulationstation/roms",
    ]

    total_roms = 0
    for base_dir in rom_base_dirs:
        if os.path.exists(base_dir):
            print(f"  ✅ ROM directory found: {base_dir}")
            try:
                systems = os.listdir(base_dir)
                for system in systems:
                    system_path = os.path.join(base_dir, system)
                    if os.path.isdir(system_path):
                        rom_files = []
                        try:
                            for file in os.listdir(system_path):
                                if file.lower().endswith(
                                    (
                                        ".zip",
                                        ".nes",
                                        ".gb",
                                        ".gbc",
                                        ".smc",
                                        ".sfc",
                                        ".bin",
                                        ".rom",
                                    )
                                ):
                                    rom_files.append(file)
                            if rom_files:
                                print(f"    📁 {system}: {len(rom_files)} ROMs")
                                total_roms += len(rom_files)
                        except PermissionError:
                            print(f"    ⚠️  {system}: Permission denied")
            except Exception as e:
                print(f"  ⚠️  Error scanning ROMs: {e}")
        else:
            print(f"  ❌ ROM directory not found: {base_dir}")

    if total_roms > 0:
        print(f"  ✅ Total ROMs found: {total_roms}")
        return True
    else:
        print(f"  ❌ No ROMs found")
        return False


def check_arcade_scripts():
    """Check if arcade control scripts exist and are executable."""
    print("\n🔍 Checking Arcade Scripts...")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    arcade_dir = os.path.join(script_dir, "arcade")

    if not os.path.exists(arcade_dir):
        print(f"  ❌ Arcade directory not found: {arcade_dir}")
        return False
    else:
        print(f"  ✅ Arcade directory found: {arcade_dir}")

    scripts = ["start_arcade.sh", "stop_arcade.sh"]
    all_good = True

    for script in scripts:
        script_path = os.path.join(arcade_dir, script)
        if os.path.exists(script_path):
            print(f"  ✅ Found: {script}")
            if os.access(script_path, os.X_OK):
                print(f"    ✅ Executable: {script}")
            else:
                print(f"    ❌ Not executable: {script}")
                print(f"    💡 Fix with: chmod +x {script_path}")
                all_good = False
        else:
            print(f"  ❌ Missing: {script}")
            all_good = False

    return all_good


def check_permissions():
    """Check file permissions and ownership."""
    print("\n🔍 Checking Permissions...")

    current_user = os.getenv("USER", "unknown")
    print(f"  👤 Current user: {current_user}")

    # Check if running as root (which might be needed for LED matrix)
    if os.geteuid() == 0:
        print(f"  ⚠️  Running as root - this might cause permission issues")
    else:
        print(f"  ℹ️  Running as regular user")

    # Check important directories
    check_dirs = [
        "/home/pi/RetroPie",
        "/opt/retropie",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "arcade"),
    ]

    for directory in check_dirs:
        if os.path.exists(directory):
            try:
                # Check if we can read the directory
                os.listdir(directory)
                print(f"  ✅ Can read: {directory}")
            except PermissionError:
                print(f"  ❌ Permission denied: {directory}")
            except Exception as e:
                print(f"  ⚠️  Error accessing {directory}: {e}")


def main():
    """Run all diagnostic checks."""
    print("🎮 BecaTicker Arcade Mode Diagnostic")
    print("=" * 50)

    results = {
        "retropie": check_retropie_installation(),
        "emulationstation": check_emulationstation(),
        "roms": check_roms(),
        "scripts": check_arcade_scripts(),
    }

    check_permissions()

    print("\n📊 Summary:")
    print("=" * 20)

    all_good = True
    for check, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {check.capitalize()}: {status}")
        if not result:
            all_good = False

    print(f"\n🎯 Overall Status: {'✅ READY' if all_good else '❌ ISSUES FOUND'}")

    if not all_good:
        print("\n💡 Recommendations:")
        if not results["retropie"]:
            print("  - Install RetroPie using the setup script: sudo ./setup.sh")
        if not results["emulationstation"]:
            print(
                "  - EmulationStation not found - RetroPie installation may be incomplete"
            )
        if not results["roms"]:
            print("  - Upload ROM files to /home/pi/RetroPie/roms/[system]/")
        if not results["scripts"]:
            print(
                "  - Run setup script to create arcade control scripts: sudo ./setup.sh"
            )

    return 0 if all_good else 1


if __name__ == "__main__":
    sys.exit(main())
