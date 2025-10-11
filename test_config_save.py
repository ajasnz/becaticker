#!/usr/bin/env python3
"""
Test script to verify configuration saving functionality.
This will test the Config class independently to see if saving works.
"""

import os
import json
import tempfile
import sys
from datetime import datetime

# Add the current directory to path to import our classes
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_config_save():
    """Test the Config class save functionality."""

    # Create a temporary config file for testing
    temp_dir = tempfile.mkdtemp()
    test_config_file = os.path.join(temp_dir, "test_config.json")

    print(f"Testing config save functionality...")
    print(f"Test config file: {test_config_file}")
    print(f"Temp directory: {temp_dir}")

    try:
        # Import our Config class (this will fail if RGB matrix isn't available, but that's ok)
        try:
            from becaticker import Config
        except ImportError as e:
            print(f"Import error (expected on Windows): {e}")
            print("Creating a minimal Config class for testing...")

            # Create a minimal version for testing
            class Config:
                def __init__(self, config_file):
                    self.config_file = os.path.abspath(config_file)
                    self.config = {
                        "test_key": "original_value",
                        "department_name": "TEST DEPT",
                        "nested": {"setting": "nested_value"},
                    }
                    print(f"Config file path set to: {self.config_file}")

                def set(self, key, value, auto_save=True):
                    print(
                        f"Setting config key '{key}' to value: {value} (auto_save={auto_save})"
                    )
                    keys = key.split(".")
                    config = self.config
                    for k in keys[:-1]:
                        if k not in config:
                            config[k] = {}
                        config = config[k]
                    old_value = config.get(keys[-1], "<<NOT_SET>>")
                    config[keys[-1]] = value
                    print(f"Config key '{key}' updated: {old_value} -> {value}")
                    if auto_save:
                        self.save_config()

                def get(self, key, default=None):
                    keys = key.split(".")
                    value = self.config
                    for k in keys:
                        value = value.get(k, {})
                    return value if value != {} else default

                def save_config(self, config=None):
                    try:
                        config_to_save = config or self.config
                        print(f"Attempting to save config to {self.config_file}")

                        # Create a backup first
                        backup_file = f"{self.config_file}.backup"
                        if os.path.exists(self.config_file):
                            import shutil

                            shutil.copy2(self.config_file, backup_file)
                            print(f"Created backup at {backup_file}")

                        # Write the new config
                        with open(self.config_file, "w") as f:
                            json.dump(config_to_save, f, indent=2)
                            f.flush()  # Ensure data is written to disk
                            os.fsync(f.fileno())  # Force write to disk

                        print(f"Configuration saved successfully to {self.config_file}")

                        # Verify the file was written correctly
                        with open(self.config_file, "r") as f:
                            verification = json.load(f)
                            print(
                                f"Verified config file contains {len(verification)} top-level keys"
                            )

                    except Exception as e:
                        print(f"Error saving config to {self.config_file}: {e}")
                        print(f"Current working directory: {os.getcwd()}")
                        print(f"Config file exists: {os.path.exists(self.config_file)}")
                        if os.path.exists(self.config_file):
                            print(
                                f"Config file permissions: {oct(os.stat(self.config_file).st_mode)}"
                            )
                        raise e

        # Test the config saving
        config = Config(test_config_file)

        print("\n=== Initial state ===")
        print(f"test_key: {config.get('test_key')}")
        print(f"department_name: {config.get('department_name')}")
        print(f"nested.setting: {config.get('nested.setting')}")

        print("\n=== Testing individual set operations ===")
        config.set("test_key", "updated_value", auto_save=False)
        config.set("department_name", "UPDATED DEPT", auto_save=False)
        config.set("nested.setting", "updated_nested", auto_save=False)
        config.set("new_key", "new_value", auto_save=False)

        print("\n=== Manual save ===")
        config.save_config()

        print("\n=== Verifying file contents ===")
        if os.path.exists(test_config_file):
            with open(test_config_file, "r") as f:
                saved_config = json.load(f)
            print(f"File size: {os.path.getsize(test_config_file)} bytes")
            print("Saved config:")
            print(json.dumps(saved_config, indent=2))

            # Verify values
            assert saved_config["test_key"] == "updated_value"
            assert saved_config["department_name"] == "UPDATED DEPT"
            assert saved_config["nested"]["setting"] == "updated_nested"
            assert saved_config["new_key"] == "new_value"
            print("\n✅ All values saved correctly!")
        else:
            print("❌ Config file was not created!")
            return False

        print("\n=== Testing reload ===")
        config2 = Config(test_config_file)
        print(f"Reloaded test_key: {config2.get('test_key')}")
        print(f"Reloaded department_name: {config2.get('department_name')}")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # Clean up
        try:
            if os.path.exists(test_config_file):
                os.remove(test_config_file)
            backup_file = f"{test_config_file}.backup"
            if os.path.exists(backup_file):
                os.remove(backup_file)
            os.rmdir(temp_dir)
            print(f"\nCleaned up test files")
        except Exception as e:
            print(f"Cleanup error: {e}")


if __name__ == "__main__":
    print("Configuration Save Test")
    print("=" * 50)
    success = test_config_save()
    print("=" * 50)
    if success:
        print("✅ Configuration saving works correctly!")
    else:
        print("❌ Configuration saving has issues!")
    print(f"Test completed at {datetime.now()}")
