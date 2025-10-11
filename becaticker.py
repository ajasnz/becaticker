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
                    "face_color": [64, 64, 64],
                    "hour_hand_color": [255, 255, 255],
                    "minute_hand_color": [255, 255, 0],
                    "second_hand_color": [255, 0, 0],
                    "number_color": [0, 255, 255],
                    "tick_color": [128, 128, 128],
                    "show_digital": True,
                    "digital_color": [255, 255, 255],
                    "show_date": True,
                    "date_color": [0, 255, 255],
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
                            # 7 day window
                            if start_time > now and start_time < now + timedelta(
                                days=7
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
        self.events = all_events[:30]  # Keep only next 30 events
        self.last_update = datetime.now()

        logger.info(f"Updated calendar with {len(self.events)} events")
        return self.events


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

        # Change event every 12 seconds
        if time.time() - self.event_change_time > 12:
            self.current_event_index = (self.current_event_index + 1) % len(events)
            self.event_change_time = time.time()
            self.calendar_scroll_pos = self.canvas.width

        current_event = events[self.current_event_index]

        # Format event text
        if isinstance(current_event["start"], datetime):
            start_str = current_event["start"].strftime("%m/%d %H:%M")
        else:
            start_str = current_event["start"].strftime("%m/%d")

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

        # Reset scroll when text completely off screen
        if self.calendar_scroll_pos + text_len < 0:
            self.calendar_scroll_pos = self.canvas.width


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

        return {
            "face": graphics.Color(*clock_config.get("face_color", [64, 64, 64])),
            "hour_hand": graphics.Color(
                *clock_config.get("hour_hand_color", [255, 255, 255])
            ),
            "minute_hand": graphics.Color(
                *clock_config.get("minute_hand_color", [255, 255, 0])
            ),
            "second_hand": graphics.Color(
                *clock_config.get("second_hand_color", [255, 0, 0])
            ),
            "numbers": graphics.Color(*clock_config.get("number_color", [0, 255, 255])),
            "ticks": graphics.Color(*clock_config.get("tick_color", [128, 128, 128])),
            "digital": graphics.Color(
                *clock_config.get("digital_color", [255, 255, 255])
            ),
            "date": graphics.Color(*clock_config.get("date_color", [0, 255, 255])),
        }

    def update_display(self) -> None:
        """Update the clock display with current time."""
        if not self.canvas:
            return

        # Check if second display is enabled
        if not self.config.get("second_display.enabled", False):
            return

        # Get current time
        now = datetime.now()

        # Get colors
        colors = self._get_colors()

        # Draw based on display type
        display_type = self.config.get("second_display.type", "clock")

        if display_type == "test":
            self._draw_test_pattern(colors)
        elif display_type == "clock":
            self._draw_analog_clock(colors, now)

    def _draw_analog_clock(self, colors: dict, now: datetime) -> None:
        """Draw the complete analog clock with all elements."""
        # Clear the clock area first (optional, but helps with clean rendering)

        # Draw elements in order from back to front
        # 1. Draw the outer circle/ring of the clock face
        self._draw_clock_face(colors["face"])

        # 2. Draw hour tick marks at all 12 positions
        self._draw_hour_ticks(colors["ticks"])

        # 3. Draw clock hands (hour, minute, second)
        self._draw_clock_hands(colors, now)

        # 5. Draw center dot on top of hands
        self._draw_center_point(colors["hour_hand"], radius=2)

        # 6. Draw digital time below the clock if enabled
        if self.config.get("second_display.settings.show_digital", True):
            self._draw_digital_time(colors["digital"], now)

        # 7. Draw date below digital time if enabled
        if self.config.get("second_display.settings.show_date", True):
            self._draw_date(colors["date"], now)

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

    def _draw_clock_face(self, color: graphics.Color) -> None:
        """Draw the outer circle of the analog clock face."""
        # Draw the main clock circle outline
        self._draw_circle(
            self.center_x, self.center_y, self.clock_radius, color, fill=False
        )

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

    def _draw_hour_ticks(self, color: graphics.Color) -> None:
        """Draw tick marks at all 12 hour positions."""
        import math

        for hour in range(12):
            # Calculate angle for this hour (0° = 12 o'clock, clockwise)
            angle_deg = hour * 30  # 30 degrees per hour
            angle_rad = math.radians(angle_deg - 90)  # -90 to start at top

            # Uniform tick marks since we no longer have numerals
            outer_radius = self.clock_radius - 2
            inner_radius = self.clock_radius - 7

            # Calculate tick mark endpoints
            outer_x = self.center_x + int(outer_radius * math.cos(angle_rad))
            outer_y = self.center_y + int(outer_radius * math.sin(angle_rad))
            inner_x = self.center_x + int(inner_radius * math.cos(angle_rad))
            inner_y = self.center_y + int(inner_radius * math.sin(angle_rad))

            # Draw the tick mark
            self._draw_line(inner_x, inner_y, outer_x, outer_y, color)

    def _draw_clock_hands(self, colors: dict, now: datetime) -> None:
        """Draw hour, minute, and second hands with proper proportions."""
        import math

        # Get current time components
        hours = now.hour % 12
        minutes = now.minute
        seconds = now.second

        # Calculate precise angles (0° = 12 o'clock, clockwise)
        # Hour hand moves continuously based on minutes too
        hour_angle = math.radians((hours * 30 + minutes * 0.5) - 90)
        minute_angle = math.radians((minutes * 6) - 90)
        second_angle = math.radians((seconds * 6) - 90)

        # Hand lengths proportional to the new clock radius (45)
        hour_length = self.clock_radius - 18  # ~27 pixels from center
        minute_length = self.clock_radius - 8  # ~37 pixels from center
        second_length = self.clock_radius - 5  # ~40 pixels from center

        # Calculate hand endpoints
        hour_x = self.center_x + int(hour_length * math.cos(hour_angle))
        hour_y = self.center_y + int(hour_length * math.sin(hour_angle))
        minute_x = self.center_x + int(minute_length * math.cos(minute_angle))
        minute_y = self.center_y + int(minute_length * math.sin(minute_angle))
        second_x = self.center_x + int(second_length * math.cos(second_angle))
        second_y = self.center_y + int(second_length * math.sin(second_angle))

        # Draw hands from back to front (thickest to thinnest)
        # Hour hand (thickest, shortest)
        self._draw_thick_line(
            self.center_x,
            self.center_y,
            hour_x,
            hour_y,
            colors["hour_hand"],
            thickness=2,
        )

        # Minute hand (medium thickness, medium length)
        self._draw_line(
            self.center_x, self.center_y, minute_x, minute_y, colors["minute_hand"]
        )

        # Second hand (thinnest, longest)
        self._draw_line(
            self.center_x, self.center_y, second_x, second_y, colors["second_hand"]
        )

    def _draw_digital_time(self, color: graphics.Color, now: datetime) -> None:
        """Draw digital time below the analog clock."""
        time_str = now.strftime("%H:%M:%S")

        # Calculate text positioning
        char_width = 6  # Small font character width
        text_width = len(time_str) * char_width
        text_x = self.center_x - text_width // 2

        # Position below the clock with some margin
        text_y = self.center_y + self.clock_radius + 15

        # Ensure it fits within the display bounds
        if text_y < self.height - 5:
            graphics.DrawText(
                self.canvas, self.small_font, text_x, text_y, color, time_str
            )

    def _draw_date(self, color: graphics.Color, now: datetime) -> None:
        """Draw date below the digital time."""
        date_str = now.strftime("%Y-%m-%d")

        # Calculate text positioning
        char_width = 6  # Small font character width
        text_width = len(date_str) * char_width
        text_x = self.center_x - text_width // 2

        # Position below the digital time
        text_y = self.center_y + self.clock_radius + 28

        # Ensure it fits within the display bounds
        if text_y < self.height - 5:
            graphics.DrawText(
                self.canvas, self.small_font, text_x, text_y, color, date_str
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
                self.clock_display.update_display()

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
