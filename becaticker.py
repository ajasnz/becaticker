#!/usr/bin/env python3
"""
BecaTicker - LED Matrix Display Controller

A single-chain RGB LED matrix display system featuring:
- 5x1 horizontal panels (320x64) for text display

"""

import argparse
import hashlib
import json
import logging
import math
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Dict, List, Optional, Tuple

import requests
from dateutil import parser as date_parser
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from icalendar import Calendar
from PIL import Image, ImageDraw, ImageFont
from werkzeug.utils import secure_filename
import io
import glob

# Add the RGB matrix library path
sys.path.append(
    os.path.join(os.path.dirname(__file__), "hzeller", "bindings", "python")
)

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
except ImportError as e:
    logger.error(f"Failed to import RGB matrix library: {e}")
    logger.error("Please ensure the RGB matrix library is properly installed.")
    logger.error("Run './build_rgb_matrix.sh' to build the library.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("becaticker.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for BecaTicker."""

    def __init__(self, config_file: str = "config.json"):
        # Ensure we have an absolute path to prevent issues with working directory changes
        self.config_file = os.path.abspath(config_file)
        logger.info(f"Config file path set to: {self.config_file}")
        self.default_config = {
            "department_name": "SYSTEM ERROR",
            "scrolling_messages": [
                "Failed to load configuration file",
                "Try restarting the system",
                "Or visit http://becaticker.local:5000 to configure",
            ],
            "calendar_urls": [],
            "web_port": 5000,
            "matrix_options": {
                "rows": 64,
                "cols": 64,
                "chain_length": 5,
                "parallel": 2,
                "brightness": 40,
                "gpio_mapping": "regular",
                "gpio_slowdown": 4,
                "hardware_mapping": "regular",
            },
            "display_settings": {
                "text_color": [255, 255, 255],
                "department_color": [0, 255, 255],
                "calendar_color": [255, 255, 0],
                "background_color": [0, 0, 0],
                "scroll_speed": 0.1,
                "calendar_refresh_minutes": 30,
            },
            "display_lines": [],
            "second_display": {
                "enabled": True,
                "type": "clock",
                "layout": "2x2",
                "chain": 2,
                "settings": {
                    # Clock style options
                    "clock_style": "modern",  # "classic", "modern", "minimal", "digital"
                    "face_style": "circle",  # "circle", "rounded_square", "square", "none"
                    "face_color": [32, 32, 48],  # Darker modern blue-gray
                    "face_outline": True,
                    "face_outline_color": [64, 128, 255],  # Modern blue accent
                    "face_thickness": 2,
                    # Hand styling
                    "hand_style": "modern",  # "classic", "modern", "arrow", "diamond"
                    "hour_hand_color": [255, 255, 255],
                    "minute_hand_color": [64, 192, 255],  # Modern blue
                    "second_hand_color": [255, 64, 64],  # Modern red
                    "hand_shadows": True,
                    "hand_shadow_color": [16, 16, 16],
                    # Hour markers
                    "marker_style": "dots",  # "ticks", "dots", "squares", "diamonds", "numbers"
                    "marker_positions": "all",  # "all" (12), "cardinal" (4), "major" (8)
                    "marker_color": [128, 180, 255],  # Light blue
                    "major_marker_color": [200, 220, 255],  # Lighter for 12, 3, 6, 9
                    "show_numbers": False,
                    "number_style": "modern",  # "roman", "arabic", "modern"
                    "number_color": [200, 220, 255],
                    # Center dot
                    "center_dot": True,
                    "center_dot_color": [255, 255, 255],
                    "center_dot_size": 3,
                    # Digital time display
                    "show_digital": True,
                    "digital_style": "modern",  # "classic", "modern", "segment"
                    "digital_color": [255, 255, 255],
                    "digital_background": False,
                    "digital_background_color": [0, 0, 0],
                    # Date display
                    "show_date": True,
                    "date_color": [128, 180, 255],
                    "date_format": "%Y-%m-%d",  # Customizable date format
                    # Animation and effects
                    "smooth_seconds": True,  # Smooth second hand movement
                    "glow_effect": False,  # Subtle glow around hands
                    "fade_old_position": True,  # Fade effect when hands move
                },
                "arcade_mode": {
                    "enabled": False,
                    "rom_directory": "/home/becaticker/RetroPie/roms",
                    "emulator_command": "/opt/retropie/supplementary/emulationstation/emulationstation",
                    "display_resolution": "128x128",
                    "auto_return_timeout": 300,  # Return to clock after 5 minutes of inactivity
                },
                "picture_viewer": {
                    "enabled": True,
                    "image_directory": "images/",
                    "slideshow_enabled": False,
                    "slideshow_interval": 10,  # seconds between images in slideshow
                    "fit_mode": "contain",  # "contain", "cover", "stretch", "center"
                    "background_color": [0, 0, 0],  # background color for letterboxing
                    "brightness_adjustment": 1.0,  # 0.0 to 2.0 brightness multiplier
                    "auto_rotate": True,  # rotate based on EXIF data
                    "max_file_size": 10485760,  # 10MB max file size
                    "supported_formats": ["jpg", "jpeg", "png", "bmp", "gif"],
                },
            },
            "clock_settings": {
                "face_color": [64, 64, 64],
                "hour_hand_color": [255, 255, 255],
                "minute_hand_color": [255, 255, 0],
                "second_hand_color": [255, 0, 0],
                "number_color": [0, 255, 255],
                "tick_color": [128, 128, 128],
            },
        }
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from file or create with defaults."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                # Merge with defaults to ensure all keys exist
                return {**self.default_config, **config}
            else:
                self.save_config(self.default_config)
                return self.default_config.copy()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.default_config.copy()

    def save_config(self, config: Dict = None) -> None:
        """Save configuration to file."""
        try:
            config_to_save = config or self.config
            logger.info(f"Attempting to save config to {self.config_file}")

            # Create a backup first
            backup_file = f"{self.config_file}.backup"
            if os.path.exists(self.config_file):
                import shutil

                shutil.copy2(self.config_file, backup_file)
                logger.info(f"Created backup at {backup_file}")

            # Write the new config
            with open(self.config_file, "w") as f:
                json.dump(config_to_save, f, indent=2)
                f.flush()  # Ensure data is written to disk
                os.fsync(f.fileno())  # Force write to disk

            logger.info(f"Configuration saved successfully to {self.config_file}")

            # Verify the file was written correctly
            with open(self.config_file, "r") as f:
                verification = json.load(f)
                logger.info(
                    f"Verified config file contains {len(verification)} top-level keys"
                )

        except Exception as e:
            logger.error(f"Error saving config to {self.config_file}: {e}")
            logger.error(f"Current working directory: {os.getcwd()}")
            logger.error(f"Config file exists: {os.path.exists(self.config_file)}")
            if os.path.exists(self.config_file):
                logger.error(
                    f"Config file permissions: {oct(os.stat(self.config_file).st_mode)}"
                )
            raise e

    def get(self, key: str, default=None):
        """Get configuration value."""
        keys = key.split(".")
        value = self.config
        for k in keys:
            value = value.get(k, {})
        return value if value != {} else default

    def set(self, key: str, value, auto_save: bool = True) -> None:
        """Set configuration value."""
        logger.debug(
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
        logger.debug(f"Config key '{key}' updated: {old_value} -> {value}")
        if auto_save:
            self.save_config()


class CalendarManager:
    """Manages calendar events from ICS feeds."""

    def __init__(self, config: Config):
        self.config = config
        self.events: List[Dict] = []
        self.last_update = datetime.min

    def fetch_events(self) -> List[Dict]:
        """Fetch and parse calendar events from ICS URLs."""
        calendar_urls = self.config.get("calendar_urls", [])
        if not calendar_urls:
            return []

        refresh_minutes = self.config.get(
            "display_settings.calendar_refresh_minutes", 30
        )
        if datetime.now() - self.last_update < timedelta(minutes=refresh_minutes):
            return self.events

        all_events = []

        for url in calendar_urls:
            try:
                logger.info(f"Fetching calendar from: {url}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                cal = Calendar.from_ical(response.content)

                event_count = 0
                for component in cal.walk():
                    if component.name == "VEVENT":
                        event_count += 1
                        event = {
                            "summary": str(component.get("summary", "No Title")),
                            "start": component.get("dtstart").dt,
                            "end": (
                                component.get("dtend").dt
                                if component.get("dtend")
                                else None
                            ),
                            "description": str(component.get("description", "")),
                        }

                        logger.info(
                            f"Processing event: {event['summary']} at {event['start']}"
                        )

                        # Only include future events within next 7 days
                        now = datetime.now(timezone.utc)
                        event_start = event["start"]

                        # Convert date-only events to datetime at midnight UTC
                        if not isinstance(event_start, datetime):
                            event_start = datetime.combine(
                                event_start, datetime.min.time(), tzinfo=timezone.utc
                            )
                        # Ensure timezone-aware comparison
                        elif event_start.tzinfo is None:
                            event_start = event_start.replace(tzinfo=timezone.utc)

                        start_time = event_start

                        # Normalize timezone handling
                        now = datetime.now()

                        # Convert both to naive datetime for comparison
                        if start_time.tzinfo is not None:
                            # Convert timezone-aware to local naive time
                            start_time = start_time.astimezone().replace(tzinfo=None)

                        # Ensure now is also naive (it should be by default)
                        if now.tzinfo is not None:
                            now = now.replace(tzinfo=None)

                        try:
                            # 21 day window (expanded from 7 days)
                            if start_time > now and start_time < now + timedelta(
                                days=21
                            ):
                                all_events.append(event)
                                logger.info(f"Added event: {event['summary']}")
                            else:
                                logger.info(
                                    f"Filtered out event: {event['summary']} (start: {start_time}, now: {now})"
                                )
                        except TypeError as te:
                            logger.warning(
                                f"Skipping event due to datetime comparison error: {te}"
                            )
                            continue

                logger.info(f"Processed {event_count} events from calendar")

            except Exception as e:
                logger.error(f"Error fetching calendar from {url}: {e}")

        # Sort events by start time
        all_events.sort(key=lambda x: x["start"])
        self.events = all_events[:50]  # Keep up to 50 events for 21-day window
        self.last_update = datetime.now()

        logger.info(f"Updated calendar with {len(self.events)} events")
        return self.events


class ArcadeManager:
    """Manages arcade mode functionality with RetroPie integration."""

    def __init__(self, config: Config):
        self.config = config
        self.arcade_process = None
        self.arcade_active = False
        self.last_activity = time.time()
        
        # Get ROM directory from config, with fallbacks for development
        default_rom_dir = self.config.get(
            "second_display.arcade_mode.rom_directory", "/home/becaticker/RetroPie/roms"
        )
        
        # For development, use local test ROM directory if default doesn't exist
        if not os.path.exists(default_rom_dir):
            test_rom_dir = os.path.join(os.path.dirname(__file__), "test_roms")
            if os.path.exists(test_rom_dir):
                self.rom_directory = test_rom_dir
                logger.info(f"Using development ROM directory: {test_rom_dir}")
            else:
                self.rom_directory = default_rom_dir
                logger.warning(f"Using default ROM directory (may not exist): {default_rom_dir}")
        else:
            self.rom_directory = default_rom_dir

    def is_retropie_installed(self) -> bool:
        """Check if RetroPie is installed and configured."""
        retropie_dirs = [
            "/opt/RetroPie-Setup", 
            "/opt/retropie", 
            "/home/becaticker/RetroPie",
            "/home/pi/RetroPie"  # Keep pi as fallback
        ]
        is_installed = any(os.path.exists(d) for d in retropie_dirs)
        
        # For development mode, if we're using test ROMs, consider RetroPie "installed"
        if not is_installed and "test_roms" in self.rom_directory:
            logger.info("Development mode: Skipping RetroPie installation check")
            return True
            
        return is_installed

    def get_available_roms(self) -> Dict[str, List[str]]:
        """Get list of available ROM files by system."""
        roms = {}
        logger.debug(f"Scanning ROM directory: {self.rom_directory}")
        
        if not os.path.exists(self.rom_directory):
            logger.warning(f"ROM directory does not exist: {self.rom_directory}")
            return roms

        try:
            system_dirs = os.listdir(self.rom_directory)
            logger.debug(f"Found {len(system_dirs)} potential system directories")
            
            for system_dir in system_dirs:
                system_path = os.path.join(self.rom_directory, system_dir)
                if os.path.isdir(system_path):
                    rom_files = []
                    try:
                        files = os.listdir(system_path)
                        for file in files:
                            if file.lower().endswith(
                                (".zip", ".nes", ".gb", ".gbc", ".smc", ".sfc", ".bin", ".rom")
                            ):
                                rom_files.append(file)
                        
                        if rom_files:
                            roms[system_dir] = sorted(rom_files)
                            logger.debug(f"Found {len(rom_files)} ROMs in {system_dir}")
                        else:
                            logger.debug(f"No ROMs found in {system_dir}")
                            
                    except PermissionError:
                        logger.warning(f"Permission denied accessing {system_path}")
                    except Exception as e:
                        logger.warning(f"Error scanning {system_path}: {e}")
                        
        except Exception as e:
            logger.error(f"Error scanning ROM directory {self.rom_directory}: {e}")

        total_roms = sum(len(rom_list) for rom_list in roms.values())
        logger.info(f"ROM scan complete: {total_roms} ROMs in {len(roms)} systems")
        return roms

    def start_arcade_mode(self) -> bool:
        """Start arcade mode."""
        logger.info("Starting arcade mode...")
        
        if self.arcade_active:
            logger.info("Arcade mode already active")
            return True

        # Check RetroPie installation
        retropie_installed = self.is_retropie_installed()
        logger.info(f"RetroPie installed: {retropie_installed}")
        if not retropie_installed:
            logger.error("RetroPie not installed - cannot start arcade mode")
            return False

        # Check for available ROMs
        roms = self.get_available_roms()
        total_roms = sum(len(rom_list) for rom_list in roms.values())
        logger.info(f"Found {total_roms} ROMs in {len(roms)} systems")
        if not roms:
            logger.error("No ROMs found - cannot start arcade mode")
            logger.error(f"ROM directory checked: {self.rom_directory}")
            return False

        # Check arcade script exists
        arcade_script = os.path.join(
            os.path.dirname(__file__), "arcade", "start_arcade.sh"
        )
        logger.info(f"Looking for arcade script: {arcade_script}")
        
        if not os.path.exists(arcade_script):
            logger.error(f"Arcade script not found: {arcade_script}")
            logger.error("Run setup.sh to create arcade scripts, or create the arcade directory manually")
            return False
        
        # Check if script is executable
        if not os.access(arcade_script, os.X_OK):
            logger.error(f"Arcade script not executable: {arcade_script}")
            logger.error("Fix with: chmod +x arcade/start_arcade.sh")
            return False

        try:
            logger.info("Starting arcade script...")
            # Start EmulationStation for the LED matrix
            self.arcade_process = subprocess.Popen(
                [arcade_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,
            )
            
            # Give the process a moment to start
            time.sleep(1)
            
            # Check if process started successfully
            if self.arcade_process.poll() is None:
                self.arcade_active = True
                self.last_activity = time.time()
                logger.info("Arcade mode started successfully")
                return True
            else:
                # Process exited immediately, check for errors
                stdout, stderr = self.arcade_process.communicate()
                logger.error(f"Arcade script exited immediately")
                logger.error(f"Script stdout: {stdout.decode()}")
                logger.error(f"Script stderr: {stderr.decode()}")
                return False

        except Exception as e:
            logger.error(f"Failed to start arcade mode: {e}")
            return False

    def stop_arcade_mode(self) -> bool:
        """Stop arcade mode."""
        if not self.arcade_active:
            logger.info("Arcade mode not active")
            return True

        try:
            # Stop EmulationStation and all emulators
            stop_script = os.path.join(
                os.path.dirname(__file__), "arcade", "stop_arcade.sh"
            )
            if os.path.exists(stop_script):
                subprocess.run([stop_script], check=True)

            if self.arcade_process:
                try:
                    os.killpg(os.getpgid(self.arcade_process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass  # Process already terminated
                self.arcade_process = None

            self.arcade_active = False
            logger.info("Arcade mode stopped successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to stop arcade mode: {e}")
            return False

    def check_status(self) -> Dict:
        """Check arcade mode status."""
        status = {
            "active": self.arcade_active,
            "retropie_installed": self.is_retropie_installed(),
            "roms_available": len(self.get_available_roms()),
            "last_activity": self.last_activity,
        }

        # Check if arcade process is still running
        if self.arcade_active and self.arcade_process:
            if self.arcade_process.poll() is not None:
                # Process has terminated
                self.arcade_active = False
                self.arcade_process = None
                status["active"] = False
                logger.info("Arcade process terminated, updating status")

        return status

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def should_auto_return(self) -> bool:
        """Check if arcade mode should auto-return to clock due to inactivity."""
        if not self.arcade_active:
            return False

        timeout = self.config.get("second_display.arcade_mode.auto_return_timeout", 300)
        return time.time() - self.last_activity > timeout


class PictureViewer:
    """Manages picture viewing functionality for the 2x2 display."""

    def __init__(self, config: Config):
        self.config = config
        self.picture_active = False
        self.current_image = None
        self.slideshow_active = False
        self.slideshow_thread = None
        self.image_list = []
        self.current_index = 0
        self.last_update = 0

        # Create images directory if it doesn't exist
        self.image_dir = os.path.abspath(
            self.config.get("second_display.picture_viewer.image_directory", "images/")
        )
        os.makedirs(self.image_dir, exist_ok=True)
        logger.info(f"Picture viewer initialized with directory: {self.image_dir}")

    def get_image_directory(self) -> str:
        """Get the absolute path to the image directory."""
        return self.image_dir

    def get_uploaded_images(self) -> List[Dict]:
        """Get list of uploaded images with metadata."""
        images = []
        settings = self.config.get("second_display.picture_viewer", {})
        supported_formats = settings.get(
            "supported_formats", ["jpg", "jpeg", "png", "bmp", "gif"]
        )

        try:
            for ext in supported_formats:
                pattern = os.path.join(self.image_dir, f"*.{ext}")
                for filepath in glob.glob(pattern, recursive=False):
                    try:
                        stat = os.stat(filepath)
                        filename = os.path.basename(filepath)

                        # Get image dimensions
                        with Image.open(filepath) as img:
                            width, height = img.size

                        images.append(
                            {
                                "filename": filename,
                                "filepath": filepath,
                                "size": stat.st_size,
                                "modified": stat.st_mtime,
                                "width": width,
                                "height": height,
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Error reading image {filepath}: {e}")

            # Sort by modification time (newest first)
            images.sort(key=lambda x: x["modified"], reverse=True)
            return images

        except Exception as e:
            logger.error(f"Error listing images: {e}")
            return []

    def save_uploaded_image(
        self, file_storage, filename: str = None
    ) -> Tuple[bool, str]:
        """Save an uploaded image file."""
        try:
            settings = self.config.get("second_display.picture_viewer", {})
            max_size = settings.get("max_file_size", 10485760)  # 10MB default
            supported_formats = settings.get(
                "supported_formats", ["jpg", "jpeg", "png", "bmp", "gif"]
            )

            # Check file size
            file_storage.seek(0, 2)  # Seek to end
            file_size = file_storage.tell()
            file_storage.seek(0)  # Reset to beginning

            if file_size > max_size:
                return False, f"File too large. Maximum size is {max_size // 1048576}MB"

            # Use provided filename or the original filename
            if not filename:
                filename = secure_filename(file_storage.filename)

            if not filename:
                return False, "Invalid filename"

            # Check file extension
            ext = filename.lower().split(".")[-1] if "." in filename else ""
            if ext not in supported_formats:
                return (
                    False,
                    f"Unsupported format. Supported: {', '.join(supported_formats)}",
                )

            # Create unique filename if file already exists
            base_name = ".".join(filename.split(".")[:-1])
            counter = 1
            while os.path.exists(os.path.join(self.image_dir, filename)):
                filename = f"{base_name}_{counter}.{ext}"
                counter += 1

            filepath = os.path.join(self.image_dir, filename)

            # Save the file
            file_storage.save(filepath)

            # Verify it's a valid image by trying to open it
            try:
                with Image.open(filepath) as img:
                    img.verify()
            except Exception as e:
                os.remove(filepath)  # Clean up invalid file
                return False, f"Invalid image file: {str(e)}"

            logger.info(f"Image saved successfully: {filename}")
            return True, filename

        except Exception as e:
            logger.error(f"Error saving uploaded image: {e}")
            return False, f"Upload failed: {str(e)}"

    def delete_image(self, filename: str) -> Tuple[bool, str]:
        """Delete an uploaded image."""
        try:
            filepath = os.path.join(self.image_dir, secure_filename(filename))

            if not os.path.exists(filepath):
                return False, "Image not found"

            if not filepath.startswith(self.image_dir):
                return False, "Invalid file path"

            os.remove(filepath)
            logger.info(f"Image deleted: {filename}")

            # If this was the current image, stop picture mode
            if self.current_image and self.current_image == filename:
                self.stop_picture_mode()

            return True, "Image deleted successfully"

        except Exception as e:
            logger.error(f"Error deleting image: {e}")
            return False, f"Delete failed: {str(e)}"

    def load_image(
        self, filename: str, display_size: Tuple[int, int] = (128, 128)
    ) -> Optional[Image.Image]:
        """Load and process an image for display."""
        try:
            filepath = os.path.join(self.image_dir, secure_filename(filename))

            if not os.path.exists(filepath):
                logger.error(f"Image not found: {filepath}")
                return None

            settings = self.config.get("second_display.picture_viewer", {})
            fit_mode = settings.get("fit_mode", "contain")
            bg_color = tuple(settings.get("background_color", [0, 0, 0]))
            brightness = settings.get("brightness_adjustment", 1.0)
            auto_rotate = settings.get("auto_rotate", True)

            # Load the image
            with Image.open(filepath) as img:
                # Handle transparency
                if img.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", img.size, bg_color)
                    background.paste(
                        img, mask=img.split()[-1]
                    )  # Use alpha channel as mask
                    img = background
                elif img.mode != "RGB":
                    img = img.convert("RGB")

                # Auto-rotate based on EXIF data
                if auto_rotate and hasattr(img, "_getexif"):
                    try:
                        exif = img._getexif()
                        if exif is not None:
                            orientation = exif.get(274)  # Orientation tag
                            if orientation == 3:
                                img = img.rotate(180, expand=True)
                            elif orientation == 6:
                                img = img.rotate(270, expand=True)
                            elif orientation == 8:
                                img = img.rotate(90, expand=True)
                    except Exception:
                        pass  # Ignore EXIF errors

                # Resize based on fit mode
                if fit_mode == "stretch":
                    img = img.resize(display_size, Image.Resampling.LANCZOS)
                elif fit_mode == "cover":
                    img.thumbnail(display_size, Image.Resampling.LANCZOS)
                    # Center crop to exact size
                    left = (img.width - display_size[0]) // 2
                    top = (img.height - display_size[1]) // 2
                    img = img.crop(
                        (left, top, left + display_size[0], top + display_size[1])
                    )
                elif fit_mode == "center":
                    # Center the image without scaling
                    background = Image.new("RGB", display_size, bg_color)
                    paste_x = (display_size[0] - img.width) // 2
                    paste_y = (display_size[1] - img.height) // 2
                    background.paste(img, (paste_x, paste_y))
                    img = background
                else:  # contain (default)
                    # Maintain aspect ratio, fit within display
                    img.thumbnail(display_size, Image.Resampling.LANCZOS)
                    background = Image.new("RGB", display_size, bg_color)
                    paste_x = (display_size[0] - img.width) // 2
                    paste_y = (display_size[1] - img.height) // 2
                    background.paste(img, (paste_x, paste_y))
                    img = background

                # Apply brightness adjustment
                if brightness != 1.0:
                    import numpy as np

                    img_array = np.array(img, dtype=np.float32)
                    img_array *= brightness
                    img_array = np.clip(img_array, 0, 255).astype(np.uint8)
                    img = Image.fromarray(img_array)

                return img

        except Exception as e:
            logger.error(f"Error loading image {filename}: {e}")
            return None

    def start_picture_mode(self, filename: str = None) -> bool:
        """Start picture viewing mode."""
        try:
            if filename:
                self.current_image = filename
                self.picture_active = True
                logger.info(f"Picture mode started with image: {filename}")
                return True
            else:
                # Start with first available image
                images = self.get_uploaded_images()
                if images:
                    self.current_image = images[0]["filename"]
                    self.picture_active = True
                    self.image_list = [img["filename"] for img in images]
                    self.current_index = 0
                    logger.info(
                        f"Picture mode started with first image: {self.current_image}"
                    )
                    return True
                else:
                    logger.error("No images available for picture mode")
                    return False

        except Exception as e:
            logger.error(f"Error starting picture mode: {e}")
            return False

    def stop_picture_mode(self) -> bool:
        """Stop picture viewing mode."""
        try:
            self.picture_active = False
            self.current_image = None
            self.stop_slideshow()
            logger.info("Picture mode stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping picture mode: {e}")
            return False

    def start_slideshow(self) -> bool:
        """Start automatic slideshow."""
        try:
            images = self.get_uploaded_images()
            if len(images) < 2:
                logger.warning("Need at least 2 images for slideshow")
                return False

            self.image_list = [img["filename"] for img in images]
            self.current_index = 0
            self.slideshow_active = True
            self.picture_active = True

            if self.slideshow_thread and self.slideshow_thread.is_alive():
                self.slideshow_active = False
                self.slideshow_thread.join()

            self.slideshow_thread = threading.Thread(
                target=self._slideshow_worker, daemon=True
            )
            self.slideshow_thread.start()

            logger.info("Slideshow started")
            return True

        except Exception as e:
            logger.error(f"Error starting slideshow: {e}")
            return False

    def stop_slideshow(self) -> bool:
        """Stop automatic slideshow."""
        try:
            self.slideshow_active = False
            if self.slideshow_thread and self.slideshow_thread.is_alive():
                self.slideshow_thread.join(timeout=2)
            logger.info("Slideshow stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping slideshow: {e}")
            return False

    def _slideshow_worker(self):
        """Background worker for slideshow."""
        while self.slideshow_active and self.image_list:
            try:
                settings = self.config.get("second_display.picture_viewer", {})
                interval = settings.get("slideshow_interval", 10)

                time.sleep(interval)

                if self.slideshow_active:
                    self.current_index = (self.current_index + 1) % len(self.image_list)
                    self.current_image = self.image_list[self.current_index]
                    logger.debug(f"Slideshow advanced to: {self.current_image}")

            except Exception as e:
                logger.error(f"Error in slideshow worker: {e}")
                break

    def get_current_image(self) -> Optional[str]:
        """Get the currently displayed image filename."""
        return self.current_image if self.picture_active else None

    def next_image(self) -> bool:
        """Switch to next image."""
        try:
            if not self.image_list:
                images = self.get_uploaded_images()
                self.image_list = [img["filename"] for img in images]

            if not self.image_list:
                return False

            self.current_index = (self.current_index + 1) % len(self.image_list)
            self.current_image = self.image_list[self.current_index]
            return True
        except Exception as e:
            logger.error(f"Error switching to next image: {e}")
            return False

    def previous_image(self) -> bool:
        """Switch to previous image."""
        try:
            if not self.image_list:
                images = self.get_uploaded_images()
                self.image_list = [img["filename"] for img in images]

            if not self.image_list:
                return False

            self.current_index = (self.current_index - 1) % len(self.image_list)
            self.current_image = self.image_list[self.current_index]
            return True
        except Exception as e:
            logger.error(f"Error switching to previous image: {e}")
            return False

    def is_active(self) -> bool:
        """Check if picture mode is active."""
        return self.picture_active

    def get_status(self) -> Dict:
        """Get current picture viewer status."""
        return {
            "active": self.picture_active,
            "current_image": self.current_image,
            "slideshow_active": self.slideshow_active,
            "total_images": len(self.get_uploaded_images()),
            "enabled": self.config.get("second_display.picture_viewer.enabled", True),
        }


class TextDisplay:
    """Handles text display on Chain 1 (5x1 horizontal panels)."""

    def __init__(
        self,
        matrix: RGBMatrix,
        config: Config,
        calendar_manager: CalendarManager,
        row_offset: int = 0,
    ):
        self.matrix = matrix
        self.config = config
        self.calendar_manager = calendar_manager
        self.canvas = None  # Will be set by main loop
        self.row_offset = row_offset  # For parallel chain support

        # Load fonts
        self.title_font = graphics.Font()
        self.title_font.LoadFont(os.path.join("hzeller", "fonts", "9x15B.bdf"))

        self.text_font = graphics.Font()
        self.text_font.LoadFont(os.path.join("hzeller", "fonts", "7x13.bdf"))

        self.small_font = graphics.Font()
        self.small_font.LoadFont(os.path.join("hzeller", "fonts", "6x10.bdf"))

        # Font cache for dynamic font loading
        self.font_cache = {}
        self._load_default_fonts()

        # Colors will be loaded dynamically in update_display()

        # Scrolling state
        self.scroll_pos = 0
        self.current_message_index = 0
        self.message_change_time = time.time()

        # Calendar scrolling state
        self.calendar_scroll_pos = 0
        self.current_event_index = 0
        self.event_change_time = time.time()

    def reset_message_scrolling(self):
        """Reset message scrolling state to prevent index out of range errors."""
        logger.info(
            f"Resetting message scrolling (was at index {self.current_message_index})"
        )
        self.current_message_index = 0
        self.scroll_pos = (
            self.canvas.width if hasattr(self, "canvas") and self.canvas else 0
        )
        self.message_change_time = time.time()

    def _load_default_fonts(self):
        """Pre-load commonly used fonts into cache."""
        default_fonts = [
            "4x6.bdf",
            "5x7.bdf",
            "5x8.bdf",
            "6x9.bdf",
            "6x10.bdf",
            "6x12.bdf",
            "7x13.bdf",
            "7x13B.bdf",
            "8x13.bdf",
            "8x13B.bdf",
            "9x15.bdf",
            "9x15B.bdf",
            "9x18.bdf",
            "9x18B.bdf",
            "10x20.bdf",
            "helvR12.bdf",
            "texgyre-27.bdf",
            "tom-thumb.bdf",
        ]

        for font_name in default_fonts:
            try:
                font_path = os.path.join("hzeller", "fonts", font_name)
                if os.path.exists(font_path):
                    font = graphics.Font()
                    font.LoadFont(font_path)
                    self.font_cache[font_name] = font
                    logger.debug(f"Loaded font: {font_name}")
            except Exception as e:
                logger.warning(f"Failed to load font {font_name}: {e}")

    def _get_font(self, font_name: str = None):
        """Get font object, loading it if necessary."""
        if not font_name or font_name == "default":
            return self.text_font

        if font_name in self.font_cache:
            return self.font_cache[font_name]

        # Try to load the font if not in cache
        try:
            font_path = os.path.join("hzeller", "fonts", font_name)
            if os.path.exists(font_path):
                font = graphics.Font()
                font.LoadFont(font_path)
                self.font_cache[font_name] = font
                logger.info(f"Dynamically loaded font: {font_name}")
                return font
        except Exception as e:
            logger.error(f"Failed to load font {font_name}: {e}")

        # Fall back to default font
        return self.text_font

    def _get_colors(self):
        """Get current colors from configuration."""
        text_color = self.config.get("display_settings.text_color", [255, 255, 255])
        dept_color = self.config.get("display_settings.department_color", [0, 255, 255])
        calendar_color = self.config.get(
            "display_settings.calendar_color", [255, 255, 0]
        )

        return {
            "text": graphics.Color(*text_color),
            "department": graphics.Color(*dept_color),
            "calendar": graphics.Color(*calendar_color),
        }

    def update_display(self) -> None:
        """Update the text display with current information."""
        if not self.canvas:
            return

        # Get current colors
        colors = self._get_colors()

        # Get configurable display lines
        display_lines = self.config.get("display_lines", [])

        # If no display lines configured, use default layout
        if not display_lines:
            # Default layout for backward compatibility
            dept_name = self.config.get("department_name", "DEPARTMENT")
            self._draw_centered_text(
                dept_name, self.title_font, colors["department"], 12
            )
            self._draw_scrolling_message(32, colors["text"])
            self._draw_calendar_events(52, colors["calendar"])
        else:
            # Use configurable display lines
            y_position = 12  # Start at top
            default_line_height = 20  # Default spacing between lines

            for line_config in display_lines:
                line_type = line_config.get("type", "disabled")
                line_content = line_config.get("content", "")
                line_spacing = line_config.get("spacing", default_line_height)
                line_scroll_speed = line_config.get("scroll_speed", None)
                line_bg_color = line_config.get("background_color", None)

                if line_type == "disabled":
                    continue

                # Calculate text Y position - center it within the background bar if present
                text_y_position = y_position
                if line_bg_color:
                    # Background bar spans from (y_position - 8) to (y_position - 8 + line_spacing)
                    # Center the text within this range
                    bar_start = y_position - 8
                    bar_height = line_spacing
                    text_y_position = (
                        bar_start + (bar_height // 2) + 4
                    )  # +4 for font baseline

                    self._draw_background_bar(bar_start, bar_height, line_bg_color)

                if line_type == "spacer":
                    # Spacer just adds space, no content
                    y_position += line_spacing
                    continue

                elif line_type == "department":
                    dept_name = self.config.get("department_name", "DEPARTMENT")
                    line_font = self._get_font(line_config.get("font"))
                    line_text_size = line_config.get("text_size", 1)
                    self._draw_centered_text(
                        dept_name,
                        line_font,
                        colors["department"],
                        text_y_position,
                        line_text_size,
                    )

                elif line_type == "message":
                    line_font = self._get_font(line_config.get("font"))
                    line_text_size = line_config.get("text_size", 1)
                    self._draw_scrolling_message(
                        text_y_position,
                        colors["text"],
                        line_scroll_speed,
                        line_font,
                        line_text_size,
                    )

                elif line_type == "calendar":
                    line_font = self._get_font(line_config.get("font"))
                    line_text_size = line_config.get("text_size", 1)
                    self._draw_calendar_events(
                        text_y_position,
                        colors["calendar"],
                        line_scroll_speed,
                        line_font,
                        line_text_size,
                    )

                elif line_type == "static":
                    if line_content:
                        line_font = self._get_font(line_config.get("font"))
                        line_text_size = line_config.get("text_size", 1)
                        self._draw_centered_text(
                            line_content,
                            line_font,
                            colors["text"],
                            text_y_position,
                            line_text_size,
                        )

                y_position += line_spacing

        # Note: Canvas swap is handled by main display loop

    def _draw_background_bar(self, y: int, height: int, color_rgb: List[int]) -> None:
        """Draw a full-width background color bar."""
        bg_color = graphics.Color(*color_rgb)
        # Apply row offset for parallel chain support
        y_adjusted = y + self.row_offset
        for row in range(
            max(self.row_offset, y_adjusted),
            min(self.row_offset + 64, y_adjusted + height),
        ):
            for col in range(self.canvas.width):
                self.canvas.SetPixel(
                    col, row, bg_color.red, bg_color.green, bg_color.blue
                )

    def _draw_centered_text(
        self,
        text: str,
        font: graphics.Font,
        color: graphics.Color,
        y: int,
        text_size: int = 1,
    ) -> None:
        """Draw centered text at specified y position with optional scaling."""
        if text_size > 1:
            # For scaled text, calculate width differently and draw multiple times
            char_width = font.CharacterWidth(ord("A"))  # Use average character width
            scaled_width = len(text) * char_width * text_size
            x = (self.canvas.width - scaled_width) // 2

            # Draw text with scaling by drawing multiple offset copies
            for scale_x in range(text_size):
                for scale_y in range(text_size):
                    graphics.DrawText(
                        self.canvas,
                        font,
                        x + scale_x,
                        y + scale_y + self.row_offset,
                        color,
                        text,
                    )
        else:
            text_width = sum([font.CharacterWidth(ord(c)) for c in text])
            x = (self.canvas.width - text_width) // 2
            graphics.DrawText(self.canvas, font, x, y + self.row_offset, color, text)

    def _draw_scrolling_message(
        self,
        y: int,
        color: graphics.Color = None,
        custom_scroll_speed: float = None,
        font: graphics.Font = None,
        text_size: int = 1,
    ) -> None:
        """Draw scrolling message at specified y position."""
        messages = self.config.get("scrolling_messages", ["No messages configured"])
        if not messages:
            return

        # Use provided color or default
        if color is None:
            text_color = self.config.get("display_settings.text_color", [255, 255, 255])
            color = graphics.Color(*text_color)

        # Use provided font or default
        if font is None:
            font = self.text_font

        # Check if current message index is out of bounds (can happen if messages list was reduced)
        if self.current_message_index >= len(messages):
            logger.warning(
                f"Message index {self.current_message_index} out of bounds for {len(messages)} messages. Resetting to 0."
            )
            self.current_message_index = 0
            self.scroll_pos = self.canvas.width  # Reset scroll position to start
            self.message_change_time = time.time()

        current_message = messages[self.current_message_index]

        # Draw scrolling text with scaling support
        if text_size > 1:
            # Draw text with scaling by drawing multiple offset copies
            for scale_x in range(text_size):
                for scale_y in range(text_size):
                    text_len = graphics.DrawText(
                        self.canvas,
                        font,
                        self.scroll_pos + scale_x,
                        y + scale_y + self.row_offset,
                        color,
                        current_message,
                    )
        else:
            text_len = graphics.DrawText(
                self.canvas,
                font,
                self.scroll_pos,
                y + self.row_offset,
                color,
                current_message,
            )

        # Update scroll position - use custom speed if provided, otherwise use global setting
        if custom_scroll_speed is not None:
            scroll_speed = custom_scroll_speed
        else:
            scroll_speed = self.config.get("display_settings.scroll_speed", 0.1)
        self.scroll_pos -= int(scroll_speed * 10)  # Convert to pixel movement per frame

        # Change message when text completely scrolled off screen + 2 second pause
        if self.scroll_pos + text_len < 0:
            if time.time() - self.message_change_time > 2:  # 2 second pause
                self.current_message_index = (self.current_message_index + 1) % len(
                    messages
                )
                self.scroll_pos = self.canvas.width
                self.message_change_time = time.time()
            # Keep scroll position off-screen during pause
            elif self.scroll_pos + text_len < -10:
                self.scroll_pos = -text_len - 10

    def _draw_calendar_events(
        self,
        y: int,
        color: graphics.Color = None,
        custom_scroll_speed: float = None,
        font: graphics.Font = None,
        text_size: int = 1,
    ) -> None:
        """Draw scrolling calendar events."""
        events = self.calendar_manager.fetch_events()

        # Use provided color or default
        if color is None:
            calendar_color = self.config.get(
                "display_settings.calendar_color", [255, 255, 0]
            )
            color = graphics.Color(*calendar_color)

        # Use provided font or default
        if font is None:
            font = self.small_font

        if not events:
            if text_size > 1:
                # Draw "No upcoming events" with scaling
                for scale_x in range(text_size):
                    for scale_y in range(text_size):
                        graphics.DrawText(
                            self.canvas,
                            font,
                            2 + scale_x,
                            y + scale_y + self.row_offset,
                            color,
                            "No upcoming events",
                        )
            else:
                graphics.DrawText(
                    self.canvas,
                    font,
                    2,
                    y + self.row_offset,
                    color,
                    "No upcoming events",
                )
            return

        # Check if current event index is out of bounds (can happen if events list was reduced)
        if self.current_event_index >= len(events):
            logger.warning(
                f"Event index {self.current_event_index} out of bounds for {len(events)} events. Resetting to 0."
            )
            self.current_event_index = 0
            self.calendar_scroll_pos = self.canvas.width
            self.event_change_time = time.time()

        current_event = events[self.current_event_index]

        # Format event text
        if isinstance(current_event["start"], datetime):
            start_str = current_event["start"].strftime("%d %b %H:%M")
        else:
            start_str = current_event["start"].strftime("%d %b")

        event_text = f"{start_str}: {current_event['summary']}"

        # Draw scrolling event text with scaling support
        if text_size > 1:
            # Draw text with scaling by drawing multiple offset copies
            for scale_x in range(text_size):
                for scale_y in range(text_size):
                    text_len = graphics.DrawText(
                        self.canvas,
                        font,
                        self.calendar_scroll_pos + scale_x,
                        y + scale_y + self.row_offset,
                        color,
                        event_text,
                    )
        else:
            text_len = graphics.DrawText(
                self.canvas,
                font,
                self.calendar_scroll_pos,
                y + self.row_offset,
                color,
                event_text,
            )

        # Update scroll position - use custom speed if provided, otherwise use global setting
        if custom_scroll_speed is not None:
            scroll_speed = custom_scroll_speed
        else:
            scroll_speed = self.config.get("display_settings.scroll_speed", 0.1)
        self.calendar_scroll_pos -= int(
            scroll_speed * 10
        )  # Convert to pixel movement per frame

        # Move to next event when text completely off screen (instead of time-based)
        if self.calendar_scroll_pos + text_len < 0:
            self.calendar_scroll_pos = self.canvas.width
            # Move to next event immediately when current event finishes scrolling
            self.current_event_index = (self.current_event_index + 1) % len(events)
            self.event_change_time = time.time()  # Update time for logging purposes


class ClockDisplay:
    """Handles clock display on Chain 2 (2x2 panels arranged as 128x128)."""

    def __init__(self, matrix: RGBMatrix, config: Config, row_offset: int = 64):
        self.matrix = matrix
        self.config = config
        self.canvas = None  # Will be set by main loop
        self.row_offset = row_offset  # Chain 2 starts at row 64

        # Load fonts for clock display
        self.large_font = graphics.Font()
        self.large_font.LoadFont(os.path.join("hzeller", "fonts", "9x18B.bdf"))

        self.medium_font = graphics.Font()
        self.medium_font.LoadFont(os.path.join("hzeller", "fonts", "7x13B.bdf"))

        self.small_font = graphics.Font()
        self.small_font.LoadFont(os.path.join("hzeller", "fonts", "6x10.bdf"))

        # Clock dimensions for 2x2 layout (128x128)
        self.width = 128
        self.height = 128
        self.center_x = self.width // 2
        self.center_y = self.height // 2
        # Use a conservative radius that ensures everything fits well within the display
        self.clock_radius = 60  # Reduced radius to ensure all elements fit properly

        # For 2x2 layout, we need to map logical coordinates to physical panel coordinates
        # Each panel is 64x64, arranged as:
        # [Panel0: 0,0-63,63] [Panel1: 64,0-127,63]
        # [Panel2: 0,64-63,127] [Panel3: 64,64-127,127]
        # But in chain format it's: Panel0, Panel1, Panel2, Panel3 linearly

    def _map_2x2_coordinates(self, logical_x: int, logical_y: int) -> tuple:
        """Map logical 2x2 coordinates to physical panel coordinates.

        For a 2x2 arrangement of 64x64 panels in a chain:
        Chain 2 with 4 panels arranged as 2x2 but connected linearly:

        Physical chain layout: [Panel0][Panel1][Panel2][Panel3] = 256 pixels wide
        Logical 2x2 layout:
        [Panel0: 0,0-63,63] [Panel1: 64,0-127,63]
        [Panel2: 0,64-63,127] [Panel3: 64,64-127,127]

        Returns (physical_x, physical_y) for the canvas.
        """
        # For a simple linear mapping, map 2x2 to linear chain
        # This assumes the panels are wired: TopLeft, TopRight, BottomLeft, BottomRight

        # Determine which panel (0-3) based on logical coordinates
        panel_x = logical_x // 64  # 0 or 1
        panel_y = logical_y // 64  # 0 or 1

        # Position within the panel (0-63, 0-63)
        local_x = logical_x % 64
        local_y = logical_y % 64

        # Clean snake pattern mapping for rewired panels
        # Chain: Panel1(BL) -> Panel2(BR) -> Panel3(TR) -> Panel4(TL)
        # Physical layout:
        # [Panel4: TL] [Panel3: TR]
        # [Panel1: BL] [Panel2: BR]
        # Corrected mapping based on observations:
        # Top-right (offset 128) is correct
        # Bottom-left (offset 0) is missing -> try different offset
        # Bottom-right shows top-left -> wrong mapping
        # Top-left shows bottom-right -> wrong mapping
        # Correct mapping based on colored bar test results:
        # Logical top-left (bars 1-8) -> Physical top-right panel (offset 128)
        # Logical top-right (bars 9-16) -> Physical top-left panel (offset 0)
        # Logical bottom-left -> Physical bottom-left panel (try offset we haven't used)
        # Logical bottom-right (bars 8-1 reversed) -> Physical bottom-right panel (offset 64)
        if panel_y == 0:  # Logical top row
            if panel_x == 0:  # Logical top-left -> Try offset 64 (was working before)
                panel_offset = 64
            else:  # Logical top-right -> Keep offset 128 (this is working)
                panel_offset = 128
        else:  # Logical bottom row
            if panel_x == 0:  # Logical bottom-left -> Found at offset 256
                panel_offset = 256  # This works!
            else:  # Logical bottom-right -> Try the missing offset 192
                panel_offset = 192  # Switch from 64 to 192

        physical_x = local_x + panel_offset
        physical_y = local_y + self.row_offset

        return physical_x, physical_y

    def _set_pixel(self, logical_x: int, logical_y: int, color: graphics.Color) -> None:
        """Set a pixel using logical 2x2 coordinates."""
        if 0 <= logical_x < self.width and 0 <= logical_y < self.height:
            physical_x, physical_y = self._map_2x2_coordinates(logical_x, logical_y)
            # Make sure we don't exceed canvas bounds
            if physical_x < self.canvas.width and physical_y < self.canvas.height:
                self.canvas.SetPixel(
                    physical_x, physical_y, color.red, color.green, color.blue
                )

    def _get_colors(self):
        """Get current colors from configuration."""
        clock_config = self.config.get("second_display.settings", {})

        # Debug logging to help troubleshoot configuration issues
        if (
            hasattr(self, "_last_config_debug")
            and time.time() - self._last_config_debug > 30
        ):
            logger.info(
                f"Clock config debug - face_style: {clock_config.get('face_style', 'NOT_SET')}"
            )
            logger.info(
                f"Clock config debug - hand_style: {clock_config.get('hand_style', 'NOT_SET')}"
            )
            logger.info(
                f"Clock config debug - marker_style: {clock_config.get('marker_style', 'NOT_SET')}"
            )
            self._last_config_debug = time.time()
        elif not hasattr(self, "_last_config_debug"):
            self._last_config_debug = time.time()

        return {
            # Face colors
            "face": graphics.Color(*clock_config.get("face_color", [32, 32, 48])),
            "face_outline": graphics.Color(
                *clock_config.get("face_outline_color", [64, 128, 255])
            ),
            # Hand colors
            "hour_hand": graphics.Color(
                *clock_config.get("hour_hand_color", [255, 255, 255])
            ),
            "minute_hand": graphics.Color(
                *clock_config.get("minute_hand_color", [64, 192, 255])
            ),
            "second_hand": graphics.Color(
                *clock_config.get("second_hand_color", [255, 64, 64])
            ),
            "hand_shadow": graphics.Color(
                *clock_config.get("hand_shadow_color", [16, 16, 16])
            ),
            # Marker colors
            "markers": graphics.Color(
                *clock_config.get("marker_color", [128, 180, 255])
            ),
            "major_markers": graphics.Color(
                *clock_config.get("major_marker_color", [200, 220, 255])
            ),
            "numbers": graphics.Color(
                *clock_config.get("number_color", [200, 220, 255])
            ),
            # Center dot
            "center_dot": graphics.Color(
                *clock_config.get("center_dot_color", [255, 255, 255])
            ),
            # Digital display
            "digital": graphics.Color(
                *clock_config.get("digital_color", [255, 255, 255])
            ),
            "digital_bg": graphics.Color(
                *clock_config.get("digital_background_color", [0, 0, 0])
            ),
            # Date display
            "date": graphics.Color(*clock_config.get("date_color", [128, 180, 255])),
            # Legacy compatibility
            "ticks": graphics.Color(*clock_config.get("tick_color", [128, 128, 128])),
        }

    def update_display(self, arcade_manager=None, picture_viewer=None) -> None:
        """Update the clock display with current time, or show arcade/picture mode status."""
        if not self.canvas:
            return

        # Check if second display is enabled
        if not self.config.get("second_display.enabled", False):
            return

        # Check if arcade mode is active (highest priority)
        if arcade_manager and arcade_manager.arcade_active:
            self._draw_arcade_mode_status(arcade_manager)
            return

        # Check if picture viewer is active (second priority)
        if picture_viewer and picture_viewer.is_active():
            self._draw_picture_mode(picture_viewer)
            return

        # Get current time
        now = datetime.now()

        # Get colors
        colors = self._get_colors()

        # Draw based on display type
        display_type = self.config.get("second_display.type", "clock")

        if display_type == "test":
            self._draw_test_pattern(colors)
        elif display_type == "arcade":
            if arcade_manager:
                self._draw_arcade_selection(arcade_manager, colors)
            else:
                self._draw_arcade_unavailable(colors)
        elif display_type == "picture":
            if picture_viewer:
                self._draw_picture_viewer_selection(picture_viewer, colors)
            else:
                self._draw_picture_unavailable(colors)
        elif display_type == "clock":
            self._draw_analog_clock(colors, now)

    def _draw_analog_clock(self, colors: dict, now: datetime) -> None:
        """Draw the complete modern analog clock with all elements."""
        config = self.config.get("second_display.settings", {})

        # Draw elements in order from back to front

        # 1. Draw the clock face (circle, square, etc.)
        self._draw_clock_face(colors)

        # 2. Draw hour markers (dots, ticks, squares, etc.)
        self._draw_hour_markers(colors)

        # 3. Draw clock hands with modern styling
        self._draw_modern_clock_hands(colors, now)

        # 4. Draw center dot if enabled
        if config.get("center_dot", True):
            center_size = config.get("center_dot_size", 3)
            self._draw_center_point(colors["center_dot"], radius=center_size)

        # 5. Draw digital time below the clock if enabled
        if config.get("show_digital", True):
            self._draw_modern_digital_time(colors, now)

        # 6. Draw date below digital time if enabled
        if config.get("show_date", True):
            self._draw_modern_date(colors, now)

    def _draw_test_pattern(self, colors: dict) -> None:
        """Draw colored bars spanning full width to test coordinate mapping."""
        # Draw horizontal colored bars across the full 128-pixel width
        # This will help us see which physical panels are being addressed

        # Bar colors for different Y positions
        test_colors = [
            graphics.Color(255, 0, 0),  # Red - Y=0-7
            graphics.Color(0, 255, 0),  # Green - Y=8-15
            graphics.Color(0, 0, 255),  # Blue - Y=16-23
            graphics.Color(255, 255, 0),  # Yellow - Y=24-31
            graphics.Color(255, 0, 255),  # Magenta - Y=32-39
            graphics.Color(0, 255, 255),  # Cyan - Y=40-47
            graphics.Color(255, 255, 255),  # White - Y=48-55
            graphics.Color(128, 128, 128),  # Gray - Y=56-63
            graphics.Color(255, 128, 0),  # Orange - Y=64-71
            graphics.Color(128, 255, 0),  # Lime - Y=72-79
            graphics.Color(128, 0, 255),  # Purple - Y=80-87
            graphics.Color(255, 128, 128),  # Pink - Y=88-95
            graphics.Color(128, 255, 255),  # Light cyan - Y=96-103
            graphics.Color(255, 255, 128),  # Light yellow - Y=104-111
            graphics.Color(64, 64, 64),  # Dark gray - Y=112-119
            graphics.Color(192, 192, 192),  # Light gray - Y=120-127
        ]

        # Draw bars using logical coordinates (_set_pixel)
        for bar_index in range(16):
            y_start = bar_index * 8
            color = test_colors[bar_index]

            # Draw full-width bar (X from 0 to 127)
            for x in range(128):
                for y in range(y_start, y_start + 8):  # Each bar is 8 pixels tall
                    if y < 128:  # Stay within bounds
                        self._set_pixel(x, y, color)

        # Also draw direct physical reference bars to see the actual panel order
        # These bypass _set_pixel and go directly to physical coordinates
        border_color = graphics.Color(255, 255, 255)  # White borders

        # Draw white borders around each physical panel (64 pixels wide each)
        for panel_offset in [0, 64, 128, 192]:
            # Top border
            for x in range(64):
                physical_x = x + panel_offset
                physical_y = 0 + self.row_offset
                if physical_x < self.canvas.width and physical_y < self.canvas.height:
                    self.canvas.SetPixel(
                        physical_x,
                        physical_y,
                        border_color.red,
                        border_color.green,
                        border_color.blue,
                    )

            # Bottom border
            for x in range(64):
                physical_x = x + panel_offset
                physical_y = 63 + self.row_offset
                if physical_x < self.canvas.width and physical_y < self.canvas.height:
                    self.canvas.SetPixel(
                        physical_x,
                        physical_y,
                        border_color.red,
                        border_color.green,
                        border_color.blue,
                    )

    def _draw_circle(
        self, cx: int, cy: int, radius: int, color: graphics.Color, fill: bool = False
    ) -> None:
        """Draw a circle using Bresenham's algorithm."""
        x = 0
        y = radius
        d = 3 - 2 * radius

        def draw_circle_points(cx, cy, x, y):
            points = [
                (cx + x, cy + y),
                (cx - x, cy + y),
                (cx + x, cy - y),
                (cx - x, cy - y),
                (cx + y, cy + x),
                (cx - y, cy + x),
                (cx + y, cy - x),
                (cx - y, cy - x),
            ]
            for px, py in points:
                self._set_pixel(px, py, color)

        while y >= x:
            if fill:
                # Fill the circle by drawing horizontal lines
                for i in range(-x, x + 1):
                    for j in [cy + y, cy - y]:
                        self._set_pixel(cx + i, j, color)
                    for j in [cy + x, cy - x]:
                        if x != y:  # Avoid drawing the same line twice
                            self._set_pixel(cx + i, j, color)
            else:
                draw_circle_points(cx, cy, x, y)

            x += 1
            if d > 0:
                y -= 1
                d = d + 4 * (x - y) + 10
            else:
                d = d + 4 * x + 6

    def _draw_line(
        self, x0: int, y0: int, x1: int, y1: int, color: graphics.Color
    ) -> None:
        """Draw a line using Bresenham's algorithm."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        x, y = x0, y0

        while True:
            self._set_pixel(x, y, color)

            if x == x1 and y == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def _draw_thick_line(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        color: graphics.Color,
        thickness: int = 2,
    ) -> None:
        """Draw a thick line by drawing multiple parallel lines."""
        for i in range(thickness):
            for j in range(thickness):
                self._draw_line(
                    x0 + i - thickness // 2,
                    y0 + j - thickness // 2,
                    x1 + i - thickness // 2,
                    y1 + j - thickness // 2,
                    color,
                )

    def _draw_center_point(self, color: graphics.Color, radius: int = 2) -> None:
        """Draw a center point (dot) at the center of the clock."""
        self._draw_circle(self.center_x, self.center_y, radius, color, fill=True)

    def _draw_clock_face(self, colors: dict) -> None:
        """Draw the clock face with modern styling options."""
        config = self.config.get("second_display.settings", {})
        face_style = config.get("face_style", "circle")
        face_color = colors.get("face", graphics.Color(32, 32, 48))
        outline_color = colors.get("face_outline", graphics.Color(64, 128, 255))

        if face_style == "none":
            return

        if face_style == "circle":
            # Modern circle with better anti-aliasing effect
            self._draw_modern_circle(face_color, outline_color)
        elif face_style == "rounded_square":
            self._draw_rounded_square(face_color, outline_color)
        elif face_style == "square":
            self._draw_square_face(face_color, outline_color)

    def _draw_modern_circle(
        self, face_color: graphics.Color, outline_color: graphics.Color
    ) -> None:
        """Draw a modern circle with improved rendering to reduce straight segments."""
        # Draw multiple concentric circles with varying opacity to create smoother appearance
        config = self.config.get("second_display.settings", {})
        thickness = config.get("face_thickness", 2)
        show_outline = config.get("face_outline", True)

        if show_outline:
            # Draw thicker outline for modern look
            for i in range(thickness):
                self._draw_circle(
                    self.center_x,
                    self.center_y,
                    self.clock_radius - i,
                    outline_color,
                    fill=False,
                )

        # Optional: Add subtle inner glow effect
        if config.get("glow_effect", False):
            glow_color = graphics.Color(
                min(255, outline_color.red + 32),
                min(255, outline_color.green + 32),
                min(255, outline_color.blue + 32),
            )
            self._draw_circle(
                self.center_x,
                self.center_y,
                self.clock_radius - thickness - 1,
                glow_color,
                fill=False,
            )

    def _draw_rounded_square(
        self, face_color: graphics.Color, outline_color: graphics.Color
    ) -> None:
        """Draw a rounded square clock face."""
        config = self.config.get("second_display.settings", {})
        thickness = config.get("face_thickness", 2)
        corner_radius = min(12, self.clock_radius // 5)  # Responsive corner radius

        # Draw rounded rectangle outline
        self._draw_rounded_rectangle(
            self.center_x - self.clock_radius + 10,
            self.center_y - self.clock_radius + 10,
            self.center_x + self.clock_radius - 10,
            self.center_y + self.clock_radius - 10,
            corner_radius,
            outline_color,
            thickness,
        )

    def _draw_square_face(
        self, face_color: graphics.Color, outline_color: graphics.Color
    ) -> None:
        """Draw a square clock face."""
        config = self.config.get("second_display.settings", {})
        thickness = config.get("face_thickness", 2)

        # Draw square outline
        size = self.clock_radius - 10
        for i in range(thickness):
            self._draw_rectangle(
                self.center_x - size + i,
                self.center_y - size + i,
                self.center_x + size - i,
                self.center_y + size - i,
                outline_color,
            )

    def _draw_rounded_rectangle(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        radius: int,
        color: graphics.Color,
        thickness: int = 1,
    ) -> None:
        """Draw a rounded rectangle outline."""
        # Draw the four sides
        for t in range(thickness):
            # Top and bottom sides
            self._draw_line(x1 + radius, y1 + t, x2 - radius, y1 + t, color)
            self._draw_line(x1 + radius, y2 - t, x2 - radius, y2 - t, color)

            # Left and right sides
            self._draw_line(x1 + t, y1 + radius, x1 + t, y2 - radius, color)
            self._draw_line(x2 - t, y1 + radius, x2 - t, y2 - radius, color)

        # Draw corner arcs (simplified as small circles)
        corners = [
            (x1 + radius, y1 + radius),  # Top-left
            (x2 - radius, y1 + radius),  # Top-right
            (x1 + radius, y2 - radius),  # Bottom-left
            (x2 - radius, y2 - radius),  # Bottom-right
        ]

        for cx, cy in corners:
            self._draw_circle(cx, cy, radius, color, fill=False)

    def _draw_rectangle(
        self, x1: int, y1: int, x2: int, y2: int, color: graphics.Color
    ) -> None:
        """Draw a rectangle outline."""
        # Top and bottom
        self._draw_line(x1, y1, x2, y1, color)
        self._draw_line(x1, y2, x2, y2, color)
        # Left and right
        self._draw_line(x1, y1, x1, y2, color)
        self._draw_line(x2, y1, x2, y2, color)

    def _draw_roman_numerals(self, color: graphics.Color) -> None:
        """Draw Roman numerals at 12, 3, 6, 9 positions inside the clock face."""
        import math

        # Position numerals well inside the clock face
        # Use a radius that keeps numerals comfortably inside the circle
        numeral_radius = self.clock_radius - 12  # Much closer to center for safety

        # Roman numerals with their positions
        # Using precise angle calculations for perfect positioning
        numerals = [
            ("XII", 0),  # 12 o'clock (top)
            ("III", 90),  # 3 o'clock (right)
            ("VI", 180),  # 6 o'clock (bottom)
            ("IX", 270),  # 9 o'clock (left)
        ]

        for numeral, angle_deg in numerals:
            # Convert angle to radians, with 0° at top (12 o'clock position)
            angle_rad = math.radians(angle_deg - 90)

            # Calculate the center position for the numeral
            numeral_center_x = self.center_x + int(numeral_radius * math.cos(angle_rad))
            numeral_center_y = self.center_y + int(numeral_radius * math.sin(angle_rad))

            # Estimate text dimensions for centering
            # Small font is approximately 6 pixels wide per character, 10 pixels tall
            char_width = 6
            char_height = 10
            text_width = len(numeral) * char_width
            text_height = char_height

            # Calculate text position (top-left corner for DrawText)
            text_x = numeral_center_x - text_width // 2
            text_y = numeral_center_y + text_height // 2  # DrawText uses baseline

            # Ensure the text stays within bounds
            text_x = max(0, min(text_x, self.width - text_width))
            text_y = max(text_height, min(text_y, self.height))

            # Draw the Roman numeral
            graphics.DrawText(
                self.canvas, self.small_font, text_x, text_y, color, numeral
            )

    def _draw_hour_markers(self, colors: dict) -> None:
        """Draw modern hour markers with various styles."""
        import math

        config = self.config.get("second_display.settings", {})
        marker_style = config.get("marker_style", "dots")
        marker_positions = config.get("marker_positions", "all")
        marker_color = colors.get("markers", graphics.Color(128, 180, 255))
        major_marker_color = colors.get("major_markers", graphics.Color(200, 220, 255))

        # Determine which positions to draw
        if marker_positions == "cardinal":
            positions = [0, 3, 6, 9]  # 12, 3, 6, 9 o'clock
        elif marker_positions == "major":
            positions = [0, 1, 3, 4, 6, 7, 9, 10]  # Every other hour
        else:  # "all"
            positions = list(range(12))

        for hour in positions:
            # Calculate angle for this hour (0° = 12 o'clock, clockwise)
            angle_deg = hour * 30  # 30 degrees per hour
            angle_rad = math.radians(angle_deg - 90)  # -90 to start at top

            # Determine if this is a major position (12, 3, 6, 9)
            is_major = hour in [0, 3, 6, 9]
            current_color = major_marker_color if is_major else marker_color

            if marker_style == "dots":
                self._draw_marker_dot(angle_rad, current_color, is_major)
            elif marker_style == "squares":
                self._draw_marker_square(angle_rad, current_color, is_major)
            elif marker_style == "diamonds":
                self._draw_marker_diamond(angle_rad, current_color, is_major)
            elif marker_style == "numbers":
                self._draw_marker_number(angle_rad, hour, current_color, is_major)
            else:  # "ticks" - improved version
                self._draw_marker_tick(angle_rad, current_color, is_major)

        # Draw numbers if enabled separately from markers
        if config.get("show_numbers", False):
            self._draw_hour_numbers(colors)

    def _draw_marker_dot(
        self, angle_rad: float, color: graphics.Color, is_major: bool
    ) -> None:
        """Draw a dot marker."""
        radius = 3 if is_major else 2
        marker_distance = self.clock_radius - 8

        dot_x = self.center_x + int(marker_distance * math.cos(angle_rad))
        dot_y = self.center_y + int(marker_distance * math.sin(angle_rad))

        self._draw_circle(dot_x, dot_y, radius, color, fill=True)

    def _draw_marker_square(
        self, angle_rad: float, color: graphics.Color, is_major: bool
    ) -> None:
        """Draw a square marker."""
        size = 3 if is_major else 2
        marker_distance = self.clock_radius - 8

        center_x = self.center_x + int(marker_distance * math.cos(angle_rad))
        center_y = self.center_y + int(marker_distance * math.sin(angle_rad))

        # Draw filled square
        for dx in range(-size, size + 1):
            for dy in range(-size, size + 1):
                self._set_pixel(center_x + dx, center_y + dy, color)

    def _draw_marker_diamond(
        self, angle_rad: float, color: graphics.Color, is_major: bool
    ) -> None:
        """Draw a diamond marker."""
        size = 3 if is_major else 2
        marker_distance = self.clock_radius - 8

        center_x = self.center_x + int(marker_distance * math.cos(angle_rad))
        center_y = self.center_y + int(marker_distance * math.sin(angle_rad))

        # Draw diamond shape
        for i in range(-size, size + 1):
            width = size - abs(i)
            for j in range(-width, width + 1):
                self._set_pixel(center_x + i, center_y + j, color)

    def _draw_marker_tick(
        self, angle_rad: float, color: graphics.Color, is_major: bool
    ) -> None:
        """Draw an improved tick marker."""
        # Different lengths for major vs minor ticks
        if is_major:
            outer_radius = self.clock_radius - 2
            inner_radius = self.clock_radius - 10
            thickness = 2
        else:
            outer_radius = self.clock_radius - 3
            inner_radius = self.clock_radius - 7
            thickness = 1

        # Calculate tick mark endpoints
        outer_x = self.center_x + int(outer_radius * math.cos(angle_rad))
        outer_y = self.center_y + int(outer_radius * math.sin(angle_rad))
        inner_x = self.center_x + int(inner_radius * math.cos(angle_rad))
        inner_y = self.center_y + int(inner_radius * math.sin(angle_rad))

        # Draw thick tick for major positions
        if thickness > 1:
            self._draw_thick_line(inner_x, inner_y, outer_x, outer_y, color, thickness)
        else:
            self._draw_line(inner_x, inner_y, outer_x, outer_y, color)

    def _draw_marker_number(
        self, angle_rad: float, hour: int, color: graphics.Color, is_major: bool
    ) -> None:
        """Draw number markers."""
        marker_distance = self.clock_radius - 15

        center_x = self.center_x + int(marker_distance * math.cos(angle_rad))
        center_y = self.center_y + int(marker_distance * math.sin(angle_rad))

        # Convert hour to display number (0 -> 12)
        display_hour = 12 if hour == 0 else hour
        number_str = str(display_hour)

        # Estimate text dimensions for centering
        char_width = 6
        char_height = 10
        text_width = len(number_str) * char_width

        # Calculate text position (top-left corner for DrawText)
        text_x = center_x - text_width // 2
        text_y = center_y + char_height // 2

        # Draw the number
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, color, number_str
        )

    def _draw_hour_numbers(self, colors: dict) -> None:
        """Draw hour numbers (1-12) around the clock face."""
        import math

        config = self.config.get("second_display.settings", {})
        number_style = config.get("number_style", "modern")
        number_color = colors.get("numbers", graphics.Color(200, 220, 255))
        number_distance = self.clock_radius - 18

        for hour in range(12):
            angle_deg = hour * 30
            angle_rad = math.radians(angle_deg - 90)

            center_x = self.center_x + int(number_distance * math.cos(angle_rad))
            center_y = self.center_y + int(number_distance * math.sin(angle_rad))

            if number_style == "roman":
                numbers = [
                    "XII",
                    "I",
                    "II",
                    "III",
                    "IV",
                    "V",
                    "VI",
                    "VII",
                    "VIII",
                    "IX",
                    "X",
                    "XI",
                ]
                number_str = numbers[hour]
            else:  # "arabic" or "modern"
                display_hour = 12 if hour == 0 else hour
                number_str = str(display_hour)

            # Center the text
            char_width = 6
            char_height = 10
            text_width = len(number_str) * char_width
            text_x = center_x - text_width // 2
            text_y = center_y + char_height // 2

            graphics.DrawText(
                self.canvas, self.small_font, text_x, text_y, number_color, number_str
            )

    def _draw_modern_clock_hands(self, colors: dict, now: datetime) -> None:
        """Draw modern styled clock hands with enhanced visuals."""
        import math

        config = self.config.get("second_display.settings", {})
        hand_style = config.get("hand_style", "modern")
        show_shadows = config.get("hand_shadows", True)
        smooth_seconds = config.get("smooth_seconds", True)

        # Get current time components
        hours = now.hour % 12
        minutes = now.minute
        seconds = now.second
        microseconds = now.microsecond if smooth_seconds else 0

        # Calculate precise angles (0° = 12 o'clock, clockwise)
        # Hour hand moves continuously based on minutes
        hour_angle = math.radians((hours * 30 + minutes * 0.5) - 90)
        minute_angle = math.radians((minutes * 6 + seconds * 0.1) - 90)

        # Smooth second hand movement if enabled
        if smooth_seconds:
            second_angle = math.radians((seconds * 6 + microseconds * 0.000006) - 90)
        else:
            second_angle = math.radians((seconds * 6) - 90)

        # Modern hand proportions
        hour_length = self.clock_radius - 22
        minute_length = self.clock_radius - 10
        second_length = self.clock_radius - 6

        # Calculate hand endpoints
        hour_x = self.center_x + int(hour_length * math.cos(hour_angle))
        hour_y = self.center_y + int(hour_length * math.sin(hour_angle))
        minute_x = self.center_x + int(minute_length * math.cos(minute_angle))
        minute_y = self.center_y + int(minute_length * math.sin(minute_angle))
        second_x = self.center_x + int(second_length * math.cos(second_angle))
        second_y = self.center_y + int(second_length * math.sin(second_angle))

        # Draw shadows first if enabled
        if show_shadows:
            shadow_offset = 1
            shadow_color = colors.get("hand_shadow", graphics.Color(16, 16, 16))

            # Hour hand shadow
            self._draw_modern_hand(
                self.center_x + shadow_offset,
                self.center_y + shadow_offset,
                hour_x + shadow_offset,
                hour_y + shadow_offset,
                shadow_color,
                hand_style,
                "hour",
            )

            # Minute hand shadow
            self._draw_modern_hand(
                self.center_x + shadow_offset,
                self.center_y + shadow_offset,
                minute_x + shadow_offset,
                minute_y + shadow_offset,
                shadow_color,
                hand_style,
                "minute",
            )

        # Draw hands from back to front
        # Hour hand (thickest, shortest)
        self._draw_modern_hand(
            self.center_x,
            self.center_y,
            hour_x,
            hour_y,
            colors["hour_hand"],
            hand_style,
            "hour",
        )

        # Minute hand (medium thickness, medium length)
        self._draw_modern_hand(
            self.center_x,
            self.center_y,
            minute_x,
            minute_y,
            colors["minute_hand"],
            hand_style,
            "minute",
        )

        # Second hand (thinnest, longest) - no shadow for clean look
        self._draw_modern_hand(
            self.center_x,
            self.center_y,
            second_x,
            second_y,
            colors["second_hand"],
            hand_style,
            "second",
        )

    def _draw_modern_hand(
        self,
        x0: int,
        y0: int,
        x1: int,
        y1: int,
        color: graphics.Color,
        style: str,
        hand_type: str,
    ) -> None:
        """Draw a single modern-styled clock hand."""
        if style == "arrow":
            self._draw_arrow_hand(x0, y0, x1, y1, color, hand_type)
        elif style == "diamond":
            self._draw_diamond_hand(x0, y0, x1, y1, color, hand_type)
        elif style == "modern":
            self._draw_tapered_hand(x0, y0, x1, y1, color, hand_type)
        else:  # "classic"
            thickness = {"hour": 3, "minute": 2, "second": 1}[hand_type]
            if thickness > 1:
                self._draw_thick_line(x0, y0, x1, y1, color, thickness)
            else:
                self._draw_line(x0, y0, x1, y1, color)

    def _draw_tapered_hand(
        self, x0: int, y0: int, x1: int, y1: int, color: graphics.Color, hand_type: str
    ) -> None:
        """Draw a tapered hand that's thicker at the center and thinner at the tip."""
        import math

        # Calculate hand vector
        dx = x1 - x0
        dy = y1 - y0
        length = math.sqrt(dx * dx + dy * dy)

        if length == 0:
            return

        # Normalize direction vector
        unit_x = dx / length
        unit_y = dy / length

        # Perpendicular vector for hand width
        perp_x = -unit_y
        perp_y = unit_x

        # Hand width based on type
        base_width = {"hour": 2.5, "minute": 1.5, "second": 0.5}[hand_type]

        # Draw hand as a series of lines with decreasing width
        segments = int(length)
        for i in range(segments):
            progress = i / segments
            width = base_width * (1 - progress * 0.7)  # Taper to 30% of original width

            # Current position along the hand
            curr_x = x0 + int(unit_x * i)
            curr_y = y0 + int(unit_y * i)

            # Draw cross-section
            offset_x = int(perp_x * width)
            offset_y = int(perp_y * width)

            self._draw_line(
                curr_x - offset_x,
                curr_y - offset_y,
                curr_x + offset_x,
                curr_y + offset_y,
                color,
            )

    def _draw_arrow_hand(
        self, x0: int, y0: int, x1: int, y1: int, color: graphics.Color, hand_type: str
    ) -> None:
        """Draw an arrow-style hand with pointed tip."""
        # Draw main line
        thickness = {"hour": 2, "minute": 2, "second": 1}[hand_type]
        if thickness > 1:
            self._draw_thick_line(x0, y0, x1, y1, color, thickness)
        else:
            self._draw_line(x0, y0, x1, y1, color)

        # Add arrow tip for hour and minute hands
        if hand_type != "second":
            import math

            # Calculate arrow head
            dx = x1 - x0
            dy = y1 - y0
            length = math.sqrt(dx * dx + dy * dy)

            if length > 0:
                # Unit vector pointing backward
                unit_x = -dx / length
                unit_y = -dy / length

                # Arrow head size
                arrow_size = {"hour": 4, "minute": 3}[hand_type]

                # Arrow head points
                arrow_x1 = x1 + int(unit_x * arrow_size - unit_y * arrow_size / 2)
                arrow_y1 = y1 + int(unit_y * arrow_size + unit_x * arrow_size / 2)
                arrow_x2 = x1 + int(unit_x * arrow_size + unit_y * arrow_size / 2)
                arrow_y2 = y1 + int(unit_y * arrow_size - unit_x * arrow_size / 2)

                # Draw arrow head
                self._draw_line(x1, y1, arrow_x1, arrow_y1, color)
                self._draw_line(x1, y1, arrow_x2, arrow_y2, color)

    def _draw_diamond_hand(
        self, x0: int, y0: int, x1: int, y1: int, color: graphics.Color, hand_type: str
    ) -> None:
        """Draw a hand with diamond-shaped tip."""
        # Draw main line
        thickness = {"hour": 2, "minute": 1, "second": 1}[hand_type]
        if thickness > 1:
            self._draw_thick_line(x0, y0, x1, y1, color, thickness)
        else:
            self._draw_line(x0, y0, x1, y1, color)

        # Add diamond tip
        if hand_type != "second":
            diamond_size = {"hour": 3, "minute": 2}[hand_type]
            self._draw_circle(x1, y1, diamond_size, color, fill=True)

    def _draw_modern_digital_time(self, colors: dict, now: datetime) -> None:
        """Draw modern digital time below the analog clock."""
        config = self.config.get("second_display.settings", {})
        digital_style = config.get("digital_style", "modern")
        show_background = config.get("digital_background", False)

        # Format time based on style
        if digital_style == "segment":
            time_str = now.strftime("%H:%M")  # Simpler for segment style
        else:
            time_str = now.strftime("%H:%M:%S")

        # Calculate text positioning
        char_width = 6  # Small font character width
        text_width = len(time_str) * char_width
        text_x = self.center_x - text_width // 2

        # Position below the clock with some margin
        text_y = self.center_y + self.clock_radius + 15

        # Ensure it fits within the display bounds
        if text_y < self.height - 5:
            # Draw background if enabled
            if show_background:
                bg_color = colors.get("digital_bg", graphics.Color(0, 0, 0))
                padding = 2
                # Draw background rectangle
                for x in range(text_x - padding, text_x + text_width + padding):
                    for y in range(text_y - 8, text_y + 2):
                        if 0 <= x < self.width and 0 <= y < self.height:
                            self._set_pixel(x, y, bg_color)

            # Draw text with style
            if digital_style == "segment":
                self._draw_segment_style_text(
                    text_x, text_y, time_str, colors["digital"]
                )
            else:
                graphics.DrawText(
                    self.canvas,
                    self.small_font,
                    text_x,
                    text_y,
                    colors["digital"],
                    time_str,
                )

    def _draw_segment_style_text(
        self, x: int, y: int, text: str, color: graphics.Color
    ) -> None:
        """Draw text in a 7-segment display style (simplified)."""
        # This is a simplified version - you could expand this for full 7-segment rendering
        # For now, just use a different font or add some visual effects
        graphics.DrawText(self.canvas, self.medium_font, x, y, color, text)

    def _draw_modern_date(self, colors: dict, now: datetime) -> None:
        """Draw modern date below the digital time."""
        config = self.config.get("second_display.settings", {})
        date_format = config.get("date_format", "%Y-%m-%d")

        date_str = now.strftime(date_format)

        # Calculate text positioning
        char_width = 6  # Small font character width
        text_width = len(date_str) * char_width
        text_x = self.center_x - text_width // 2

        # Position below the digital time
        text_y = self.center_y + self.clock_radius + 28

        # Ensure it fits within the display bounds
        if text_y < self.height - 5:
            graphics.DrawText(
                self.canvas, self.small_font, text_x, text_y, colors["date"], date_str
            )

    def _draw_arcade_mode_status(self, arcade_manager) -> None:
        """Draw arcade mode status when arcade is running."""
        # Clear the display area with a dark background
        bg_color = graphics.Color(16, 16, 32)
        for x in range(self.width):
            for y in range(self.height):
                self._set_pixel(x, y, bg_color)

        # Draw "ARCADE MODE" text
        text_color = graphics.Color(0, 255, 0)  # Green
        text = "ARCADE"
        text_x = self.center_x - len(text) * 3
        text_y = self.center_y - 10
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, text_color, text
        )

        text = "ACTIVE"
        text_x = self.center_x - len(text) * 3
        text_y = self.center_y + 5
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, text_color, text
        )

        # Draw activity indicator (blinking dot)
        if int(time.time() * 2) % 2:  # Blink every 0.5 seconds
            indicator_color = graphics.Color(255, 0, 0)  # Red
            self._draw_circle(
                self.center_x + 30, self.center_y, 3, indicator_color, fill=True
            )

    def _draw_arcade_selection(self, arcade_manager, colors: dict) -> None:
        """Draw arcade mode ROM selection interface."""
        roms = arcade_manager.get_available_roms()

        if not roms:
            self._draw_arcade_unavailable(colors)
            return

        # Clear background
        bg_color = graphics.Color(0, 16, 32)
        for x in range(self.width):
            for y in range(self.height):
                self._set_pixel(x, y, bg_color)

        # Draw title
        title_color = graphics.Color(255, 255, 0)
        text = "ARCADE"
        text_x = self.center_x - len(text) * 3
        text_y = 15
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, title_color, text
        )

        # Show ROM count
        total_roms = sum(len(rom_list) for rom_list in roms.values())
        rom_text = f"{total_roms} ROMs"
        text_x = self.center_x - len(rom_text) * 3
        text_y = 30
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, colors["digital"], rom_text
        )

        # Show systems available
        y_pos = 50
        for system, rom_list in list(roms.items())[:3]:  # Show first 3 systems
            system_text = f"{system.upper()}: {len(rom_list)}"
            text_x = 5
            graphics.DrawText(
                self.canvas,
                self.small_font,
                text_x,
                y_pos,
                colors["markers"],
                system_text,
            )
            y_pos += 15

        # Draw instruction
        instruction = "Web UI to start"
        text_x = self.center_x - len(instruction) * 3
        text_y = self.height - 15
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, colors["date"], instruction
        )

    def _draw_arcade_unavailable(self, colors: dict) -> None:
        """Draw message when arcade mode is not available."""
        # Clear background
        bg_color = graphics.Color(32, 16, 16)
        for x in range(self.width):
            for y in range(self.height):
                self._set_pixel(x, y, bg_color)

        # Draw error message
        error_color = graphics.Color(255, 128, 128)
        text = "ARCADE"
        text_x = self.center_x - len(text) * 3
        text_y = self.center_y - 15
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, error_color, text
        )

        text = "UNAVAILABLE"
        text_x = self.center_x - len(text) * 3
        text_y = self.center_y
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, error_color, text
        )

        text = "No ROMs found"
        text_x = self.center_x - len(text) * 3
        text_y = self.center_y + 15
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, colors["date"], text
        )

    def _draw_picture_mode(self, picture_viewer) -> None:
        """Draw the current image in picture mode."""
        current_image = picture_viewer.get_current_image()
        if not current_image:
            self._draw_picture_unavailable({})
            return

        try:
            # Load and process the image
            image = picture_viewer.load_image(current_image, (self.width, self.height))
            if not image:
                self._draw_picture_unavailable({})
                return

            # Convert PIL image to matrix display
            rgb_array = image.load()
            for y in range(image.height):
                for x in range(image.width):
                    r, g, b = rgb_array[x, y]
                    color = graphics.Color(r, g, b)
                    self._set_pixel(x, y, color)

            # Draw image info overlay if slideshow is active
            if picture_viewer.slideshow_active:
                # Draw slideshow indicator
                indicator_color = graphics.Color(255, 255, 0)
                # Small dot in top-right corner
                for i in range(3):
                    for j in range(3):
                        self._set_pixel(self.width - 5 + i, 2 + j, indicator_color)

        except Exception as e:
            logger.error(f"Error drawing picture: {e}")
            self._draw_picture_unavailable({})

    def _draw_picture_viewer_selection(self, picture_viewer, colors: dict) -> None:
        """Draw picture viewer selection interface."""
        images = picture_viewer.get_uploaded_images()

        if not images:
            self._draw_picture_unavailable(colors)
            return

        # Clear background
        bg_color = graphics.Color(16, 0, 32)
        for x in range(self.width):
            for y in range(self.height):
                self._set_pixel(x, y, bg_color)

        # Draw title
        title_color = graphics.Color(255, 128, 255)
        text = "PICTURES"
        text_x = self.center_x - len(text) * 3
        text_y = 15
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, title_color, text
        )

        # Show image count
        image_text = f"{len(images)} Images"
        text_x = self.center_x - len(image_text) * 3
        text_y = 30
        graphics.DrawText(
            self.canvas,
            self.small_font,
            text_x,
            text_y,
            colors.get("digital", graphics.Color(255, 255, 255)),
            image_text,
        )

        # Show recent images
        y_pos = 50
        for i, img in enumerate(images[:5]):  # Show first 5 images
            filename = img["filename"]
            if len(filename) > 15:
                filename = filename[:12] + "..."

            text_x = 5
            graphics.DrawText(
                self.canvas,
                self.small_font,
                text_x,
                y_pos,
                colors.get("markers", graphics.Color(128, 128, 255)),
                filename,
            )
            y_pos += 12

        # Draw instruction
        instruction = "Upload via web"
        text_x = self.center_x - len(instruction) * 3
        text_y = self.height - 15
        graphics.DrawText(
            self.canvas,
            self.small_font,
            text_x,
            text_y,
            colors.get("date", graphics.Color(128, 180, 255)),
            instruction,
        )

    def _draw_picture_unavailable(self, colors: dict) -> None:
        """Draw message when picture viewer is not available."""
        # Clear background
        bg_color = graphics.Color(32, 16, 32)
        for x in range(self.width):
            for y in range(self.height):
                self._set_pixel(x, y, bg_color)

        # Draw error message
        error_color = graphics.Color(255, 128, 255)
        text = "PICTURES"
        text_x = self.center_x - len(text) * 3
        text_y = self.center_y - 15
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, error_color, text
        )

        text = "NO IMAGES"
        text_x = self.center_x - len(text) * 3
        text_y = self.center_y
        graphics.DrawText(
            self.canvas, self.small_font, text_x, text_y, error_color, text
        )

        text = "Upload via web"
        text_x = self.center_x - len(text) * 3
        text_y = self.center_y + 15
        graphics.DrawText(
            self.canvas,
            self.small_font,
            text_x,
            text_y,
            colors.get("date", graphics.Color(128, 128, 128)),
            text,
        )


class UserManager:
    """Manages user authentication with hashed passwords and JSON storage."""

    def __init__(self, db_file: str = "users.db"):
        self.db_file = db_file
        self.users = self.load_users()

    def load_users(self) -> Dict:
        """Load users from JSON file or create default admin user."""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, "r") as f:
                    return json.load(f)
            else:
                # Create default admin user with hashed password
                default_users = {
                    "admin": {
                        "password_hash": self.hash_password("becaticker123"),
                        "role": "admin",
                        "created": datetime.now().isoformat(),
                        "last_login": None,
                        "active": True,
                    }
                }
                self.save_users(default_users)
                logger.info(
                    "Created default admin user (username: admin, password: becaticker123)"
                )
                return default_users
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return {}

    def save_users(self, users: Dict = None) -> None:
        """Save users to JSON file."""
        try:
            users_to_save = users or self.users
            with open(self.db_file, "w") as f:
                json.dump(users_to_save, f, indent=2)
            logger.info("Users database saved successfully")
        except Exception as e:
            logger.error(f"Error saving users: {e}")

    def hash_password(self, password: str) -> str:
        """Hash a password using SHA256 with salt."""
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        try:
            salt, hash_part = password_hash.split(":")
            return hashlib.sha256((password + salt).encode()).hexdigest() == hash_part
        except ValueError:
            return False

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user and return user info if successful."""
        if username not in self.users:
            return None

        user = self.users[username]
        if not user.get("active", True):
            return None

        if self.verify_password(password, user["password_hash"]):
            # Update last login
            self.users[username]["last_login"] = datetime.now().isoformat()
            self.save_users()

            # Return user info without password hash
            user_info = user.copy()
            user_info.pop("password_hash", None)
            user_info["username"] = username
            return user_info

        return None

    def create_user(self, username: str, password: str, role: str = "user") -> bool:
        """Create a new user."""
        if username in self.users:
            return False

        self.users[username] = {
            "password_hash": self.hash_password(password),
            "role": role,
            "created": datetime.now().isoformat(),
            "last_login": None,
            "active": True,
        }
        self.save_users()
        logger.info(f"Created new user: {username}")
        return True

    def update_user_password(self, username: str, new_password: str) -> bool:
        """Update a user's password."""
        if username not in self.users:
            return False

        self.users[username]["password_hash"] = self.hash_password(new_password)
        self.save_users()
        logger.info(f"Updated password for user: {username}")
        return True

    def delete_user(self, username: str) -> bool:
        """Delete a user (mark as inactive)."""
        if username not in self.users or username == "admin":  # Protect admin user
            return False

        self.users[username]["active"] = False
        self.save_users()
        logger.info(f"Deactivated user: {username}")
        return True

    def list_users(self) -> List[Dict]:
        """List all active users (without password hashes)."""
        users = []
        for username, user_data in self.users.items():
            if user_data.get("active", True):
                user = user_data.copy()
                user["username"] = username
                user.pop("password_hash", None)
                users.append(user)
        return users

    def is_admin(self, username: str) -> bool:
        """Check if a user has admin role."""
        if username in self.users:
            return self.users[username].get("role") == "admin"
        return False


# Authentication Configuration
AUTH_CONFIG = {"enabled": True, "session_timeout": 3600}  # 1 hour in seconds


def login_required(f):
    """Decorator to require authentication for routes."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not AUTH_CONFIG["enabled"]:
            return f(*args, **kwargs)

        if "authenticated" not in session or not session["authenticated"]:
            if request.is_json:
                return (
                    jsonify({"status": "error", "message": "Authentication required"}),
                    401,
                )
            return redirect(url_for("login"))

        # Check session timeout
        if "login_time" in session:
            login_time = session["login_time"]
            if time.time() - login_time > AUTH_CONFIG["session_timeout"]:
                session.clear()
                if request.is_json:
                    return (
                        jsonify({"status": "error", "message": "Session expired"}),
                        401,
                    )
                return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


class BecaTicker:
    """Main application class coordinating all display components."""

    def __init__(self):
        self.config = Config()
        self.user_manager = UserManager()
        self.calendar_manager = CalendarManager(self.config)
        self.arcade_manager = ArcadeManager(self.config)
        self.picture_viewer = PictureViewer(self.config)

        # Initialize single chain matrix with 5x1 text panels
        self.matrix = self._create_matrix()

        # Initialize displays with different row offsets for parallel chains
        self.text_display = TextDisplay(
            self.matrix, self.config, self.calendar_manager, row_offset=0
        )

        # Initialize second display (2x2 clock display on chain 2)
        self.clock_display = ClockDisplay(self.matrix, self.config, row_offset=64)

        # Threading
        self.running = False
        self.display_thread = None

        # Web interface
        self.app = Flask(__name__)
        self.app.secret_key = self.config.get("flask_secret_key", secrets.token_hex(32))
        self._setup_web_routes()

    def _create_matrix(self) -> RGBMatrix:
        """Create and configure an RGB matrix."""
        options = RGBMatrixOptions()

        chain_config = self.config.get("matrix_options", {})

        options.rows = chain_config.get("rows", 64)
        options.cols = chain_config.get("cols", 64)
        options.chain_length = chain_config.get("chain_length", 4)
        options.parallel = chain_config.get("parallel", 1)
        options.brightness = chain_config.get("brightness", 40)
        options.hardware_mapping = chain_config.get("hardware_mapping", "regular")
        options.gpio_slowdown = chain_config.get("gpio_slowdown", 2)
        options.drop_privileges = False
        options.disable_hardware_pulsing = True

        # Additional anti-flickering options for long chains
        if chain_config.get("chain_length", 1) >= 4:
            options.limit_refresh_rate_hz = 120  # Limit refresh rate for stability
            options.show_refresh_rate = False  # Don't show refresh rate counter

        return RGBMatrix(options=options)

    def _setup_web_routes(self) -> None:
        """Set up Flask web interface routes."""

        @self.app.route("/")
        @login_required
        def index():
            return render_template("index.html", config=self.config.config)

        @self.app.route("/api/config", methods=["GET"])
        @login_required
        def get_config():
            return jsonify(self.config.config)

        @self.app.route("/api/config", methods=["POST"])
        @login_required
        def update_config():
            try:
                new_config = request.json
                logger.info(f"Received config update request from web interface")
                logger.info(
                    f"Config keys to update: {list(new_config.keys()) if new_config else 'None'}"
                )

                if not new_config:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "No configuration data received",
                            }
                        ),
                        400,
                    )

                # Log current config state before changes
                logger.info(
                    f"Current config has {len(self.config.config)} top-level keys"
                )

                # Update specific configuration sections (without auto-saving each one)
                if "department_name" in new_config:
                    old_value = self.config.get("department_name")
                    self.config.set(
                        "department_name",
                        new_config["department_name"],
                        auto_save=False,
                    )
                    logger.info(
                        f"Updated department_name: '{old_value}' -> '{new_config['department_name']}'"
                    )

                if "scrolling_messages" in new_config:
                    old_count = len(self.config.get("scrolling_messages", []))
                    self.config.set(
                        "scrolling_messages",
                        new_config["scrolling_messages"],
                        auto_save=False,
                    )
                    new_count = len(new_config["scrolling_messages"])
                    logger.info(
                        f"Updated scrolling_messages: {old_count} -> {new_count} messages"
                    )

                    # Reset message index to prevent index out of range errors
                    if hasattr(self, "text_display") and self.text_display:
                        self.text_display.reset_message_scrolling()

                if "calendar_urls" in new_config:
                    old_count = len(self.config.get("calendar_urls", []))
                    self.config.set(
                        "calendar_urls", new_config["calendar_urls"], auto_save=False
                    )
                    new_count = len(new_config["calendar_urls"])
                    logger.info(
                        f"Updated calendar_urls: {old_count} -> {new_count} URLs"
                    )

                # Handle new display settings
                if "display_settings" in new_config:
                    display_settings = new_config["display_settings"]
                    for key, value in display_settings.items():
                        self.config.set(
                            f"display_settings.{key}", value, auto_save=False
                        )
                        logger.info(
                            f"Updated display setting display_settings.{key}: {value}"
                        )

                # Handle display lines configuration
                if "display_lines" in new_config:
                    self.config.set(
                        "display_lines", new_config["display_lines"], auto_save=False
                    )
                    logger.info(f"Updated display lines: {new_config['display_lines']}")

                # Handle second display configuration
                if "second_display" in new_config:
                    second_display = new_config["second_display"]
                    for key, value in second_display.items():
                        if key == "settings":
                            # Handle nested settings
                            for setting_key, setting_value in value.items():
                                self.config.set(
                                    f"second_display.settings.{setting_key}",
                                    setting_value,
                                    auto_save=False,
                                )
                                logger.info(
                                    f"Updated second display setting: {setting_key} = {setting_value}"
                                )
                        else:
                            self.config.set(
                                f"second_display.{key}", value, auto_save=False
                            )
                            logger.info(f"Updated second display: {key} = {value}")

                # Handle clock settings (for backward compatibility)
                if "clock_settings" in new_config:
                    clock_settings = new_config["clock_settings"]
                    for key, value in clock_settings.items():
                        self.config.set(f"clock_settings.{key}", value, auto_save=False)
                        # Also update the second display settings for consistency
                        self.config.set(
                            f"second_display.settings.{key}", value, auto_save=False
                        )
                        logger.info(f"Updated clock setting: {key} = {value}")

                # Handle matrix options
                if "matrix_options" in new_config:
                    matrix_options = new_config["matrix_options"]
                    # Update brightness settings
                    if (
                        "chain1" in matrix_options
                        and "brightness" in matrix_options["chain1"]
                    ):
                        self.config.set(
                            "brightness",
                            matrix_options["chain1"]["brightness"],
                            auto_save=False,
                        )
                        logger.info(
                            f"Updated brightness: {matrix_options['chain1']['brightness']}"
                        )

                # Save the configuration to file
                logger.info("About to save configuration to file...")
                self.config.save_config()
                logger.info("Configuration save operation completed")

                return jsonify(
                    {
                        "status": "success",
                        "message": "Configuration updated successfully",
                    }
                )
            except Exception as e:
                logger.error(f"Error updating config: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/events")
        @login_required
        def get_events():
            events = self.calendar_manager.fetch_events()
            # Convert datetime objects to strings for JSON serialization
            serializable_events = []
            for event in events:
                serializable_event = event.copy()
                if isinstance(event["start"], datetime):
                    serializable_event["start"] = event["start"].isoformat()
                else:
                    serializable_event["start"] = event["start"].isoformat()
                if event["end"] and isinstance(event["end"], datetime):
                    serializable_event["end"] = event["end"].isoformat()
                serializable_events.append(serializable_event)
            return jsonify(serializable_events)

        @self.app.route("/api/second-display", methods=["GET"])
        @login_required
        def get_second_display_config():
            """Get second display configuration."""
            return jsonify(self.config.get("second_display", {}))

        @self.app.route("/api/second-display", methods=["POST"])
        @login_required
        def update_second_display_config():
            """Update second display configuration."""
            try:
                new_config = request.json
                logger.info(f"Received second display config update: {new_config}")

                if not new_config:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "No configuration data received",
                            }
                        ),
                        400,
                    )

                for key, value in new_config.items():
                    if key == "settings":
                        # Handle nested settings
                        for setting_key, setting_value in value.items():
                            self.config.set(
                                f"second_display.settings.{setting_key}",
                                setting_value,
                                auto_save=False,
                            )
                            logger.info(
                                f"Updated second display setting: {setting_key} = {setting_value}"
                            )
                    else:
                        self.config.set(f"second_display.{key}", value, auto_save=False)
                        logger.info(f"Updated second display: {key} = {value}")

                logger.info("About to save second display configuration...")
                self.config.save_config()
                logger.info("Second display configuration saved successfully")

                return jsonify(
                    {
                        "status": "success",
                        "message": "Second display configuration updated",
                    }
                )
            except Exception as e:
                logger.error(f"Error updating second display config: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/second-display/toggle", methods=["POST"])
        @login_required
        def toggle_second_display():
            """Toggle second display on/off."""
            try:
                current_enabled = self.config.get("second_display.enabled", False)
                new_enabled = not current_enabled
                self.config.set("second_display.enabled", new_enabled, auto_save=False)
                logger.info(
                    f"Toggling second display: {current_enabled} -> {new_enabled}"
                )
                self.config.save_config()

                status = "enabled" if new_enabled else "disabled"
                logger.info(f"Second display {status}")

                return jsonify(
                    {
                        "status": "success",
                        "message": f"Second display {status}",
                        "enabled": new_enabled,
                    }
                )
            except Exception as e:
                logger.error(f"Error toggling second display: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        # Authentication routes
        @self.app.route("/login", methods=["GET", "POST"])
        def login():
            if request.method == "POST":
                data = request.get_json() or request.form
                username = data.get("username", "").strip()
                password = data.get("password", "")

                user_info = self.user_manager.authenticate_user(username, password)
                if user_info:
                    session["authenticated"] = True
                    session["username"] = username
                    session["user_role"] = user_info["role"]
                    session["login_time"] = time.time()

                    if request.is_json:
                        return jsonify(
                            {"status": "success", "message": "Login successful"}
                        )
                    else:
                        return redirect("/")
                else:
                    if request.is_json:
                        return (
                            jsonify(
                                {"status": "error", "message": "Invalid credentials"}
                            ),
                            401,
                        )
                    else:
                        return render_template(
                            "login.html", error="Invalid username or password"
                        )

            return render_template("login.html")

        @self.app.route("/logout", methods=["GET", "POST"])
        def logout():
            session.clear()
            if request.is_json:
                return jsonify(
                    {"status": "success", "message": "Logged out successfully"}
                )
            else:
                return redirect("/login")

        # Arcade Mode API Routes
        @self.app.route("/api/arcade/status", methods=["GET"])
        @login_required
        def get_arcade_status():
            try:
                status = self.arcade_manager.check_status()
                roms = self.arcade_manager.get_available_roms()

                return jsonify(
                    {
                        "status": "success",
                        "arcade": {
                            "active": status["active"],
                            "retropie_installed": status["retropie_installed"],
                            "roms_available": status["roms_available"],
                            "available_systems": list(roms.keys()),
                            "rom_details": roms,
                        },
                    }
                )
            except Exception as e:
                logger.error(f"Error getting arcade status: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/arcade/start", methods=["POST"])
        @login_required
        def start_arcade():
            try:
                if self.arcade_manager.start_arcade_mode():
                    return jsonify(
                        {
                            "status": "success",
                            "message": "Arcade mode started successfully",
                        }
                    )
                else:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Failed to start arcade mode",
                            }
                        ),
                        400,
                    )
            except Exception as e:
                logger.error(f"Error starting arcade mode: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/arcade/stop", methods=["POST"])
        @login_required
        def stop_arcade():
            try:
                if self.arcade_manager.stop_arcade_mode():
                    return jsonify(
                        {
                            "status": "success",
                            "message": "Arcade mode stopped successfully",
                        }
                    )
                else:
                    return (
                        jsonify(
                            {"status": "error", "message": "Failed to stop arcade mode"}
                        ),
                        400,
                    )
            except Exception as e:
                logger.error(f"Error stopping arcade mode: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/arcade/roms", methods=["GET"])
        @login_required
        def get_roms():
            try:
                roms = self.arcade_manager.get_available_roms()
                return jsonify(
                    {
                        "status": "success",
                        "roms": roms,
                        "total_roms": sum(len(rom_list) for rom_list in roms.values()),
                    }
                )
            except Exception as e:
                logger.error(f"Error getting ROMs: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        # Picture viewer API endpoints
        @self.app.route("/api/pictures/status", methods=["GET"])
        @login_required
        def picture_status():
            try:
                status = self.picture_viewer.get_status()
                return jsonify({"status": "success", **status})
            except Exception as e:
                logger.error(f"Error getting picture status: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/pictures/list", methods=["GET"])
        @login_required
        def list_pictures():
            try:
                images = self.picture_viewer.get_uploaded_images()
                return jsonify({"status": "success", "images": images})
            except Exception as e:
                logger.error(f"Error listing pictures: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/pictures/upload", methods=["POST"])
        @login_required
        def upload_picture():
            try:
                if "file" not in request.files:
                    return (
                        jsonify({"status": "error", "message": "No file provided"}),
                        400,
                    )

                file = request.files["file"]
                if file.filename == "":
                    return (
                        jsonify({"status": "error", "message": "No file selected"}),
                        400,
                    )

                success, message = self.picture_viewer.save_uploaded_image(file)
                if success:
                    return jsonify(
                        {"status": "success", "message": f"Image uploaded: {message}"}
                    )
                else:
                    return jsonify({"status": "error", "message": message}), 400

            except Exception as e:
                logger.error(f"Error uploading picture: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/pictures/delete", methods=["POST"])
        @login_required
        def delete_picture():
            try:
                data = request.get_json()
                if not data or "filename" not in data:
                    return (
                        jsonify({"status": "error", "message": "Filename required"}),
                        400,
                    )

                success, message = self.picture_viewer.delete_image(data["filename"])
                if success:
                    return jsonify({"status": "success", "message": message})
                else:
                    return jsonify({"status": "error", "message": message}), 400

            except Exception as e:
                logger.error(f"Error deleting picture: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/pictures/start", methods=["POST"])
        @login_required
        def start_picture_viewer():
            try:
                data = request.get_json()
                filename = data.get("filename") if data else None

                if self.picture_viewer.start_picture_mode(filename):
                    return jsonify(
                        {"status": "success", "message": "Picture viewer started"}
                    )
                else:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Failed to start picture viewer",
                            }
                        ),
                        400,
                    )

            except Exception as e:
                logger.error(f"Error starting picture viewer: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/pictures/stop", methods=["POST"])
        @login_required
        def stop_picture_viewer():
            try:
                if self.picture_viewer.stop_picture_mode():
                    return jsonify(
                        {"status": "success", "message": "Picture viewer stopped"}
                    )
                else:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Failed to stop picture viewer",
                            }
                        ),
                        400,
                    )

            except Exception as e:
                logger.error(f"Error stopping picture viewer: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/pictures/slideshow/start", methods=["POST"])
        @login_required
        def start_slideshow():
            try:
                if self.picture_viewer.start_slideshow():
                    return jsonify(
                        {"status": "success", "message": "Slideshow started"}
                    )
                else:
                    return (
                        jsonify(
                            {"status": "error", "message": "Failed to start slideshow"}
                        ),
                        400,
                    )

            except Exception as e:
                logger.error(f"Error starting slideshow: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/pictures/slideshow/stop", methods=["POST"])
        @login_required
        def stop_slideshow():
            try:
                if self.picture_viewer.stop_slideshow():
                    return jsonify(
                        {"status": "success", "message": "Slideshow stopped"}
                    )
                else:
                    return (
                        jsonify(
                            {"status": "error", "message": "Failed to stop slideshow"}
                        ),
                        400,
                    )

            except Exception as e:
                logger.error(f"Error stopping slideshow: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/pictures/next", methods=["POST"])
        @login_required
        def next_picture():
            try:
                if self.picture_viewer.next_image():
                    return jsonify(
                        {"status": "success", "message": "Switched to next image"}
                    )
                else:
                    return (
                        jsonify({"status": "error", "message": "No images available"}),
                        400,
                    )

            except Exception as e:
                logger.error(f"Error switching to next picture: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/pictures/previous", methods=["POST"])
        @login_required
        def previous_picture():
            try:
                if self.picture_viewer.previous_image():
                    return jsonify(
                        {"status": "success", "message": "Switched to previous image"}
                    )
                else:
                    return (
                        jsonify({"status": "error", "message": "No images available"}),
                        400,
                    )

            except Exception as e:
                logger.error(f"Error switching to previous picture: {e}")
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/auth/status")
        def auth_status():
            authenticated = session.get("authenticated", False)
            if authenticated and "login_time" in session:
                # Check if session has expired
                if time.time() - session["login_time"] > AUTH_CONFIG["session_timeout"]:
                    session.clear()
                    authenticated = False

            return jsonify(
                {
                    "authenticated": authenticated,
                    "username": session.get("username", ""),
                    "user_role": session.get("user_role", "user"),
                    "is_admin": session.get("user_role") == "admin",
                    "auth_enabled": AUTH_CONFIG["enabled"],
                }
            )

        # User management routes (admin only)
        @self.app.route("/api/users", methods=["GET"])
        @login_required
        def list_users():
            if session.get("user_role") != "admin":
                return (
                    jsonify({"status": "error", "message": "Admin access required"}),
                    403,
                )

            users = self.user_manager.list_users()
            return jsonify(users)

        @self.app.route("/api/users", methods=["POST"])
        @login_required
        def create_user():
            if session.get("user_role") != "admin":
                return (
                    jsonify({"status": "error", "message": "Admin access required"}),
                    403,
                )

            data = request.get_json()
            username = data.get("username", "").strip()
            password = data.get("password", "")
            role = data.get("role", "user")

            if not username or not password:
                return (
                    jsonify(
                        {"status": "error", "message": "Username and password required"}
                    ),
                    400,
                )

            if len(password) < 6:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Password must be at least 6 characters",
                        }
                    ),
                    400,
                )

            if self.user_manager.create_user(username, password, role):
                return jsonify(
                    {
                        "status": "success",
                        "message": f"User '{username}' created successfully",
                    }
                )
            else:
                return (
                    jsonify({"status": "error", "message": "Username already exists"}),
                    400,
                )

        @self.app.route("/api/users/<username>", methods=["DELETE"])
        @login_required
        def delete_user(username):
            if session.get("user_role") != "admin":
                return (
                    jsonify({"status": "error", "message": "Admin access required"}),
                    403,
                )

            if username == "admin":
                return (
                    jsonify({"status": "error", "message": "Cannot delete admin user"}),
                    400,
                )

            if self.user_manager.delete_user(username):
                return jsonify(
                    {
                        "status": "success",
                        "message": f"User '{username}' deleted successfully",
                    }
                )
            else:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "User not found or cannot be deleted",
                        }
                    ),
                    400,
                )

        @self.app.route("/api/users/<username>/password", methods=["PUT"])
        @login_required
        def change_password(username):
            # Users can change their own password, admins can change any password
            current_user = session.get("username")
            is_admin = session.get("user_role") == "admin"

            if current_user != username and not is_admin:
                return jsonify({"status": "error", "message": "Unauthorized"}), 403

            data = request.get_json()
            new_password = data.get("new_password", "")

            if len(new_password) < 6:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Password must be at least 6 characters",
                        }
                    ),
                    400,
                )

            if self.user_manager.update_user_password(username, new_password):
                return jsonify(
                    {"status": "success", "message": "Password updated successfully"}
                )
            else:
                return jsonify({"status": "error", "message": "User not found"}), 400

    def start(self) -> None:
        """Start the display system."""
        logger.info("Starting BecaTicker display system")
        self.running = True

        # Start display update thread
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()

        # Start web interface
        web_port = self.config.get("web_port", 5000)
        logger.info(f"Starting web interface on port {web_port}")

        try:
            self.app.run(host="0.0.0.0", port=web_port, debug=False, threaded=True)
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop the display system."""
        logger.info("Stopping BecaTicker display system")
        self.running = False
        if self.display_thread:
            self.display_thread.join(timeout=2)

    def _display_loop(self) -> None:
        """Main display update loop."""
        logger.info("Display update loop started")

        # Create shared canvas for both displays
        canvas = self.matrix.CreateFrameCanvas()

        while self.running:
            try:
                # Clear the shared canvas
                canvas.Clear()

                # Set canvas for both displays
                self.text_display.canvas = canvas
                self.clock_display.canvas = canvas

                # Update both displays (draws to the canvas)
                self.text_display.update_display()
                self.clock_display.update_display(
                    self.arcade_manager, self.picture_viewer
                )

                # Swap the canvas buffers once
                canvas = self.matrix.SwapOnVSync(canvas)

                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in display loop: {e}")
                time.sleep(1)

        logger.info("Display update loop stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="BecaTicker LED Matrix Display Controller"
    )
    parser.add_argument(
        "--config", default="config.json", help="Configuration file path"
    )
    parser.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"]
    )

    args = parser.parse_args()

    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    try:
        # Create and start the ticker
        ticker = BecaTicker()
        ticker.start()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
