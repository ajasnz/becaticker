# Second Display Implementation

This document describes the implementation of a second logical display for the BecaTicker system.

## Overview

The second display is a 2x2 arrangement of 64x64 LED panels (total resolution: 128x128) that operates as a separate logical display from the existing 5x1 horizontal panel chain.

## Hardware Configuration

- **Chain 1**: 5x64x64 panels in horizontal arrangement (320x64 resolution) - existing text display
- **Chain 2**: 4x64x64 panels in 2x2 arrangement (128x128 resolution) - new clock display

## Wiring

The second display is connected to **chain 2** of the parallel setup:
- The panels are wired in a standard chain configuration
- The 2x2 arrangement uses a U-mapper or similar pixel mapping
- Each panel is 64x64 pixels
- Total resolution is 128x128 pixels

## Software Architecture

### Classes

#### `ClockDisplay`
- Handles rendering on the second display
- Supports analog clock with digital time and date
- Row offset of 64 to target chain 2 pixels
- Configurable colors and display options

#### Configuration Structure
```json
{
  "second_display": {
    "enabled": true,
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
      "show_digital": true,
      "digital_color": [255, 255, 255],
      "show_date": true,
      "date_color": [0, 255, 255]
    }
  }
}
```

### Matrix Configuration

The matrix options have been updated to support parallel chains:

```json
{
  "matrix_options": {
    "rows": 64,
    "cols": 64,
    "chain_length": 5,
    "parallel": 2,
    "chain2_length": 4,
    "brightness": 40,
    "hardware_mapping": "regular",
    "gpio_slowdown": 4,
    "pixel_mapper_config": "U-mapper"
  }
}
```

### Display Loop

The main display loop has been updated to handle both displays:

1. Clear the shared canvas
2. Set canvas for both displays
3. Update text display (chain 1, rows 0-63)
4. Update clock display (chain 2, rows 64-127)
5. Swap canvas buffers

## API Endpoints

### GET /api/second-display
Returns the current second display configuration.

### POST /api/second-display
Updates the second display configuration. Accepts JSON with any second display settings.

Example:
```json
{
  "enabled": true,
  "settings": {
    "show_digital": false,
    "hour_hand_color": [255, 0, 0]
  }
}
```

### POST /api/second-display/toggle
Toggles the second display on/off.

## Row Offset System

The system uses row offsets to handle parallel chains:

- **Chain 1** (Text Display): Row offset 0 (pixels 0-63)
- **Chain 2** (Clock Display): Row offset 64 (pixels 64-127)

When drawing to the canvas, each display adds its row offset to the Y coordinates to ensure pixels are written to the correct chain.

## Display Features

### Analog Clock
- 12-hour clock face with Roman numerals
- Hour, minute, and second hands in different colors
- Configurable colors for all elements
- Center dot at clock center

### Digital Time (Optional)
- HH:MM:SS format below the analog clock
- Configurable color
- Can be disabled

### Date Display (Optional)
- YYYY-MM-DD format below digital time
- Configurable color
- Can be disabled

## Testing

Run the test script to verify the implementation:

```bash
python test_second_display.py
```

## Usage

1. Connect your 2x2 panel arrangement to chain 2
2. Update `config.json` to enable the second display
3. Start the application: `python becaticker.py`
4. Configure via web interface at http://becaticker.local:5000
5. Use API endpoints for programmatic control

## Future Enhancements

- Support for other display types (weather, calendar, custom images)
- Animation effects
- Multiple clock time zones
- Custom layouts and positioning
- Integration with external data sources