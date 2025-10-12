#!/usr/bin/env python3
"""
Test script to verify arcade mode functionality
"""

import os
import sys
import time
import requests
import json


def test_arcade_api():
    """Test the arcade mode API endpoints"""
    base_url = "http://localhost:5000"

    print("🎮 Testing Arcade Mode API")
    print("=" * 40)

    # Test status endpoint
    try:
        print("📊 Testing arcade status...")
        response = requests.get(f"{base_url}/api/arcade/status")
        if response.status_code == 200:
            status = response.json()
            print(f"  ✅ Status: {json.dumps(status, indent=2)}")
        else:
            print(f"  ❌ Status failed: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Status error: {e}")

    # Test ROMs endpoint
    try:
        print("\n📦 Testing ROM listing...")
        response = requests.get(f"{base_url}/api/arcade/roms")
        if response.status_code == 200:
            roms = response.json()
            print(f"  ✅ ROMs: {json.dumps(roms, indent=2)}")
        else:
            print(f"  ❌ ROMs failed: {response.status_code}")
    except Exception as e:
        print(f"  ❌ ROMs error: {e}")

    # Test start arcade mode
    try:
        print("\n🚀 Testing arcade start...")
        response = requests.post(f"{base_url}/api/arcade/start")
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Start: {json.dumps(result, indent=2)}")

            # Wait a moment then check status
            time.sleep(2)
            response = requests.get(f"{base_url}/api/arcade/status")
            if response.status_code == 200:
                status = response.json()
                print(f"  📊 Status after start: {json.dumps(status, indent=2)}")

        else:
            result = (
                response.json()
                if response.headers.get("content-type") == "application/json"
                else response.text
            )
            print(f"  ❌ Start failed: {response.status_code} - {result}")
    except Exception as e:
        print(f"  ❌ Start error: {e}")

    # Test stop arcade mode
    try:
        print("\n🛑 Testing arcade stop...")
        response = requests.post(f"{base_url}/api/arcade/stop")
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Stop: {json.dumps(result, indent=2)}")
        else:
            result = (
                response.json()
                if response.headers.get("content-type") == "application/json"
                else response.text
            )
            print(f"  ❌ Stop failed: {response.status_code} - {result}")
    except Exception as e:
        print(f"  ❌ Stop error: {e}")


def check_files():
    """Check if required files exist"""
    print("\n📁 Checking Required Files")
    print("=" * 30)

    files_to_check = [
        "arcade/start_arcade.sh",
        "arcade/stop_arcade.sh",
        "arcade/start_arcade_dev.sh",
        "arcade/stop_arcade_dev.sh",
        "test_roms/arcade/galaga.zip",
        "test_roms/nes/supermario.nes",
    ]

    for file_path in files_to_check:
        if os.path.exists(file_path):
            # Check if it's executable (for .sh files)
            if file_path.endswith(".sh"):
                if os.access(file_path, os.X_OK):
                    print(f"  ✅ {file_path} (executable)")
                else:
                    print(f"  ⚠️  {file_path} (not executable)")
            else:
                print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")


def main():
    """Main test function"""
    print("🧪 BecaTicker Arcade Mode Test")
    print("=" * 50)

    # Check files first
    check_files()

    # Test API
    test_arcade_api()

    print("\n✅ Test completed!")


if __name__ == "__main__":
    main()
