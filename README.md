# BecaTicker - LED Matrix Display Controller

> This readme was AI generated fromm the code base. It has not yet been checked for accuracy. ***USE COMMON SENSE***.

Professional RGB LED matrix display system for Raspberry Pi featuring dual-chain configuration with web-based management.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Hardware Setup](#hardware-setup)
- [Installation](#installation)
- [Configuration](#configuration)
- [Web Interface](#web-interface)
- [API Documentation](#api-documentation)
- [System Management](#system-management)
- [Development Guide](#development-guide)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Security](#security)
- [Performance](#performance)
- [File Structure](#file-structure)
- [Technical Specifications](#technical-specifications)

## Overview

BecaTicker is a sophisticated LED matrix display controller designed for professional environments. It manages two independent chains of RGB LED panels to display different types of content simultaneously:

- **Primary Display (Chain 1)**: 5×1 panels for scrolling text, announcements, and calendar events
- **Secondary Display (Chain 2)**: 2×2 panels for analog clock and image display

The system provides a complete web-based management interface, real-time calendar integration, and robust production-ready features including logging, health monitoring, and user management.

## Features

### Display Capabilities
- **Dual-Chain Architecture**: Independent control of two display areas
- **Text Display**: Scrolling messages with customizable speed, colors, and formatting
- **Calendar Integration**: Real-time iCal/ICS calendar event display
- **Analog Clock**: Customizable clock with multiple hand styles and colors
- **Picture Viewer**: Image display with slideshow capabilities
- **Dynamic Content**: Real-time updates without service interruption
- **Startup Display**: Automatic IP address and port display for 30 seconds on startup

### Management & Control
- **Web Interface**: Complete browser-based configuration and control
- **REST API**: Programmatic access to all system functions
- **User Management**: Secure authentication with admin controls
- **Real-time Monitoring**: Live status updates and health checking
- **Configuration Management**: JSON-based settings with web UI

### Production Features
- **Systemd Integration**: Proper Linux service with auto-restart
- **Comprehensive Logging**: Structured logging with rotation
- **Health Monitoring**: Built-in diagnostics and status reporting
- **Error Recovery**: Automatic recovery from display errors
- **Security**: Authentication, session management, and access controls

## System Architecture

### Overview Diagram
```
┌─────────────────┬─────────────────┐
│   Web Browser   │   REST Client   │
│   (Port 5000)   │   (API Access)  │
└─────────┬───────┴─────────┬───────┘
          │                 │
          ▼                 ▼
    ┌─────────────────────────────┐
    │      Flask Web App          │
    │  - Authentication           │
    │  - Configuration UI         │  
    │  - REST API Endpoints       │
    └─────────┬───────────────────┘
              │
              ▼
    ┌─────────────────────────────┐
    │    BecaTicker Core          │
    │  - Display Management       │
    │  - Calendar Integration     │
    │  - Picture Management       │
    │  - Configuration Engine     │
    └─────────┬───────────────────┘
              │
              ▼
    ┌─────────────────────────────┐
    │   RGB Matrix Library        │
    │  - Hardware Abstraction     │
    │  - Parallel Chain Control   │
    │  - Graphics Primitives      │
    └─────────┬───────────────────┘
              │
              ▼
    ┌─────────────────────────────┐
    │     Hardware Layer          │
    │  - Raspberry Pi GPIO        │
    │  - RGB Matrix HAT           │
    │  - LED Panel Chains         │
    └─────────────────────────────┘
```

### Component Architecture

#### Core Components
- **`BecaTicker` Class**: Main application controller
- **`TextDisplay` Class**: Manages Chain 1 (5×1 panels) text rendering
- **`ClockDisplay` Class**: Manages Chain 2 (2×2 panels) clock and pictures
- **`CalendarManager` Class**: Handles iCal integration and event processing
- **`PictureViewer` Class**: Manages image display and slideshow functionality
- **`Config` Class**: Configuration management with automatic persistence
- **`UserManager` Class**: Authentication and user session management

#### Data Flow
1. **Configuration**: Web UI → Flask Routes → Config Class → JSON File
2. **Calendar Events**: iCal URLs → CalendarManager → Event Processing → Display
3. **Display Updates**: Core Classes → RGB Matrix Library → Hardware
4. **User Interaction**: Web Browser → Flask Authentication → API Endpoints

### Physical Panel Layout
```
Chain 1 (Text Display):
┌─────┬─────┬─────┬─────┬─────┐
│ P4  │ P3  │ P2  │ P1  │ P0  │  320×64 pixels
└─────┴─────┴─────┴─────┴─────┘

Chain 2 (Clock/Pictures):    ┌─────┬─────┐
                             │ P1  │ P4  │  128×128 pixels
                             ├─────┼─────┤
                             │ P2  │ P3  │
                             └─────┴─────┘
```

## Hardware Setup

### Required Components
- **Raspberry Pi 4** (4GB RAM recommended, 2GB minimum)
- **7× 64×64 RGB LED Panels** with HUB75 connectors
- **Adafruit RGB Matrix HAT** or compatible interface board
- **Power Supply**: 5V 20A minimum (adjust based on brightness needs)
- **MicroSD Card**: 32GB Class 10 or better
- **Cooling**: Heatsink and fan for Raspberry Pi (recommended)

### Wiring Configuration

#### Panel Connections
Each panel requires:
- **Power**: 5V and GND (use thick gauge wire for power distribution)
- **Data**: HUB75 connector with ribbon cable
- **Daisy Chain**: Output of one panel connects to input of next

#### Power Distribution
⚠️ **Critical**: Proper power distribution is essential
- Use thick gauge wire (16 AWG or thicker) for 5V power runs
- Distribute power at multiple points along the chain
- Monitor voltage drop - should not exceed 0.3V from supply to panel
- Consider separate power injection for panels 3+ in each chain

#### GPIO Connections (via RGB Matrix HAT)
The HAT handles the complex GPIO routing automatically. Key connections:
- **Chain 1**: Primary data lines (R1, G1, B1, etc.)
- **Chain 2**: Secondary data lines (R2, G2, B2, etc.)
- **Control Lines**: CLK, LAT, OE, A, B, C, D address lines

### Physical Installation
1. **Mount panels** in the layout shown above
2. **Connect data cables** following the chain sequence
3. **Install power distribution** with proper gauge wiring
4. **Connect Raspberry Pi** via RGB Matrix HAT
5. **Test each panel** individually before full installation

## Installation

### Prerequisites
- Raspberry Pi OS (Bullseye or newer)
- Internet connection for package downloads
- SSH access or direct terminal access

### Quick Production Deployment
```bash
# Clone repository with submodules
git clone --recurse-submodules https://github.com/ajasnz/becaticker.git
cd becaticker

# Run production deployment
sudo ./deploy.sh

# Start service
sudo systemctl start becaticker
```

### Development Installation
```bash
# Clone repository
git clone --recurse-submodules https://github.com/ajasnz/becaticker.git
cd becaticker

# Development setup
sudo ./setup.sh

# Manual start for testing
./run.sh
```

### Post-Installation Setup
1. **Start the service**: `sudo systemctl start becaticker`
2. **Watch startup display**: The 5×1 display will show the web interface URL for 30 seconds
3. **Access web interface**: Use the displayed URL or `http://[raspberry-pi-ip]:5000`
4. **Login**: Username: `admin`, Password: `becaticker123`
5. **⚠️ Change password immediately** via Settings page
6. **Configure displays**: Set brightness, colors, text speed
7. **Add calendar URLs**: Enter iCal/ICS URLs for event display
8. **Test functionality**: Verify all displays are working

**Note**: The startup display showing the web interface URL only appears once each time the service starts, making it easy to locate the web interface without needing to check network settings.

## Configuration

### Configuration File Structure
The `config.json` file contains all system settings:

```json
{
  "department_name": "Your Department",
  "scrolling_messages": [
    "Message 1",
    "Message 2"
  ],
  "calendar_urls": [
    "https://example.com/calendar.ics"
  ],
  "web_port": 5000,
  "matrix_options": {
    "brightness": 40,
    "chain_length": 5,
    "parallel": 2,
    "cols": 64,
    "rows": 64
  },
  "display_settings": {
    "scroll_speed": 0.5,
    "text_color": [255, 255, 255],
    "background_color": [0, 0, 0],
    "clock_color": [0, 255, 0]
  },
  "second_display": {
    "enabled": true,
    "type": "clock",
    "settings": {
      "show_date": true,
      "date_color": [128, 180, 255]
    }
  }
}
```

### Key Configuration Sections

#### Matrix Options
- **`brightness`**: 1-100, controls LED brightness
- **`chain_length`**: Number of panels in Chain 1 (typically 5)
- **`parallel`**: Number of parallel chains (2 for this setup)
- **`gpio_slowdown`**: Timing adjustment for different Pi models

#### Display Settings
- **`scroll_speed`**: Text scroll speed (0.1-2.0)
- **`text_color`**: RGB array for text color
- **`background_color`**: RGB array for background
- **`calendar_refresh_minutes`**: How often to update calendar events

#### Second Display (Clock)
- **`type`**: "clock", "picture", or "test"
- **`show_date`**: Whether to display date below clock
- **`date_format`**: Python strftime format string

### Runtime Configuration
Most settings can be changed via the web interface without restarting:
- Text messages and colors
- Calendar URLs
- Display brightness
- Clock appearance
- Picture slideshow settings

## Web Interface

### Main Dashboard
- **Live Status**: Real-time display of current content
- **Quick Controls**: Start/stop displays, change modes
- **System Status**: Service health, error indicators
- **Statistics**: Uptime, event counts, system resources

### Configuration Pages

#### Display Settings
- **Chain 1 (Text)**: Message content, scroll speed, colors
- **Chain 2 (Clock)**: Clock style, colors, date display
- **Brightness**: Global brightness control with preview
- **Advanced**: Matrix timing, GPIO settings

#### Calendar Management
- **Add URLs**: iCal/ICS calendar sources
- **Event Filter**: Show/hide specific event types
- **Refresh Settings**: Update frequency, timeout settings
- **Preview**: View upcoming events before display

#### Picture Management
- **Upload Images**: Support for JPG, PNG, GIF formats
- **Slideshow**: Timing, transition effects
- **Image List**: Preview, delete, reorder images
- **Display Mode**: Manual selection or automatic slideshow

#### System Settings
- **User Management**: Change passwords, add users
- **Network**: Port settings, access controls
- **Logging**: Log levels, file management
- **Backup/Restore**: Configuration export/import

### API Integration
The web interface is built on a REST API that can be used for automation:
- **Status Monitoring**: `/api/status`
- **Configuration**: `/api/config`
- **Pictures**: `/api/pictures/*`
- **System Control**: Various control endpoints

## API Documentation

### Authentication
All API endpoints require authentication via session cookies or basic auth.

### Endpoints Overview

#### System Status
```http
GET /api/status
```
Returns system health, uptime, and current display status.

Response:
```json
{
  "status": "success",
  "system": {
    "uptime": 3600,
    "memory_usage": 45.2,
    "display_active": true
  },
  "displays": {
    "text_display": "active",
    "clock_display": "active"
  }
}
```

#### Configuration Management
```http
GET /api/config
POST /api/config
```

Get or update system configuration. POST accepts partial updates.

Example update:
```json
{
  "display_settings": {
    "brightness": 60,
    "scroll_speed": 1.0
  }
}
```

#### Picture Management
```http
GET /api/pictures/status
POST /api/pictures/start
POST /api/pictures/stop
POST /api/pictures/upload
DELETE /api/pictures/{filename}
```

Manage picture display and uploaded images.

#### Error Handling
All endpoints return consistent error format:
```json
{
  "status": "error",
  "message": "Description of error",
  "code": "ERROR_CODE"
}
```

## System Management

### Service Control
```bash
# Basic service management
sudo systemctl start becaticker
sudo systemctl stop becaticker
sudo systemctl restart becaticker
sudo systemctl status becaticker

# Enable/disable auto-start
sudo systemctl enable becaticker
sudo systemctl disable becaticker
```

### Monitoring & Logs
```bash
# View real-time logs
sudo journalctl -u becaticker -f

# View application logs
tail -f logs/becaticker.log

# Run health check
./health_check.sh

# View system resources
htop
df -h
```

### Manual Updates
Auto-update has been disabled for stability. Updates can be performed manually when needed:

```bash
# Manual update process
cd /path/to/becaticker
git pull origin main

# Update Python dependencies if needed
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Rebuild RGB matrix library if needed
cd hzeller
make clean
make build-python PYTHON="../venv/bin/python"
cd bindings/python
../../../venv/bin/python setup.py install
cd ../..

# Restart service to apply changes
sudo systemctl restart becaticker

# View update logs (if update.sh was used previously)
tail -f logs/update.log
```

**Manual Update Benefits:**
- Full control over when updates are applied
- Ability to review changes before applying
- No risk of automatic updates breaking the service
- Can test updates in development before production

### Configuration Updates
```bash
# Backup current config
cp config.json config.json.backup

# Edit configuration
nano config.json

# Reload configuration (no restart needed for most changes)
# Configuration is reloaded automatically
```

### System Updates
```bash
# Update BecaTicker code
git pull
sudo systemctl restart becaticker

# Update system packages
sudo apt update && sudo apt upgrade

# Update Python dependencies
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

## Development Guide

### Development Environment Setup
```bash
# Clone with development tools
git clone --recurse-submodules https://github.com/ajasnz/becaticker.git
cd becaticker

# Install development dependencies
sudo ./setup.sh

# Run in development mode
./run.sh
```

### Code Structure

#### Main Application (`becaticker.py`)
- **Lines 1-100**: Imports, logging setup, RGB matrix initialization
- **Lines 100-300**: Configuration and utility classes
- **Lines 300-800**: Display management classes (Text, Clock, Pictures)
- **Lines 800-2000**: Core application logic and display rendering
- **Lines 2000-3000**: Flask web application and API routes
- **Lines 3000+**: Main application loop and startup

#### Key Classes and Methods

**BecaTicker Class**:
- `__init__()`: Initialize all components
- `start()`: Main application loop
- `_create_matrix()`: Hardware initialization
- `setup_flask_routes()`: Web interface setup

**TextDisplay Class**:
- `update_display()`: Render text content
- `draw_scrolling_text()`: Handle text animation
- `draw_calendar_events()`: Render calendar events

**ClockDisplay Class**:
- `update_display()`: Render clock or pictures
- `_draw_analog_clock()`: Clock rendering logic
- `_draw_picture_mode()`: Picture display logic

### Adding New Features

#### Adding a New Display Mode
1. **Define mode in config**: Add to `second_display.type` options
2. **Add rendering method**: Create `_draw_new_mode()` in ClockDisplay
3. **Update web interface**: Add controls in templates
4. **Add API endpoints**: Create routes for mode control

#### Adding New Configuration Options
1. **Update default config**: Add to `DEFAULT_CONFIG` in Config class
2. **Add web UI controls**: Update templates/index.html
3. **Add validation**: Update config validation logic
4. **Document option**: Update this README

### Testing
```bash
# Run with debug logging
LOG_LEVEL=DEBUG ./run.sh

# Test API endpoints
curl -u admin:admin http://localhost:5000/api/status

# Check configuration validation
python3 -c "from becaticker import Config; Config('test_config.json')"
```

### Debugging Common Issues
- **Import errors**: Check RGB matrix library installation
- **Display artifacts**: Adjust `gpio_slowdown` in matrix_options
- **Performance issues**: Monitor CPU/memory with htop
- **Network issues**: Check firewall and port configuration

## Troubleshooting

### Common Issues and Solutions

#### Service Won't Start
```bash
# Check service status
sudo systemctl status becaticker

# View recent logs
sudo journalctl -u becaticker -n 50

# Common causes:
# - RGB matrix library not installed
# - Permission issues
# - Configuration file errors
```

**Solution Steps**:
1. Run `./health_check.sh` for diagnostic
2. Check logs for specific error messages
3. Verify hardware connections
4. Reinstall if necessary: `sudo ./deploy.sh`

#### Display Issues

**No Display Output**:
- Check power supply voltage and current capacity
- Verify panel connections and chain sequence
- Test with lower brightness setting
- Check GPIO connections via RGB Matrix HAT

**Flickering or Artifacts**:
- Increase `gpio_slowdown` in matrix_options (try 2-4)
- Check for loose connections
- Verify power supply stability
- Reduce brightness if power-limited

**Wrong Colors or Dim Display**:
- Check color configuration in settings
- Verify power supply voltage (should be 5.0V ± 0.25V)
- Test individual panels
- Check for damaged components

#### Web Interface Issues

**Cannot Access Web Interface**:
```bash
# Check if service is running
sudo systemctl status becaticker

# Test local access
curl http://localhost:5000

# Check firewall
sudo ufw status
```

**Login Issues**:
- Default credentials: admin/becaticker123
- Reset password via direct config file edit
- Check session management in logs

#### Performance Issues

**Slow Response**:
- Check system resources: `htop`, `df -h`
- Review log files for errors
- Restart service: `sudo systemctl restart becaticker`
- Consider upgrading to Pi 4 with more RAM

**High CPU Usage**:
- Reduce display refresh rate
- Optimize scroll speed settings
- Check for infinite loops in logs

### Hardware Troubleshooting

#### Power Supply Issues
**Symptoms**: Dim displays, random failures, restarts
**Solutions**:
- Measure voltage at multiple points in chain
- Use thicker gauge wire for power distribution
- Add power injection points
- Upgrade to higher capacity supply

#### GPIO/Connection Issues
**Symptoms**: No display, wrong patterns, intermittent failures
**Solutions**:
- Reseat all connections
- Check HAT mounting and GPIO contact
- Test with known-good cables
- Verify panel compatibility (HUB75)

#### Environmental Issues
**Symptoms**: Crashes in high temperature, intermittent failures
**Solutions**:
- Add cooling for Raspberry Pi
- Monitor temperatures: `vcgencmd measure_temp`
- Ensure adequate ventilation
- Check for electrical interference

### Log Analysis

#### Important Log Messages
- **"Matrix initialized successfully"**: Hardware setup OK
- **"Failed to import RGB matrix library"**: Installation issue
- **"Configuration loaded"**: Config file parsed successfully
- **"Calendar updated with X events"**: Calendar integration working

#### Error Patterns
- **"Permission denied"**: Usually GPIO access issues
- **"Connection timeout"**: Network/calendar URL issues
- **"Memory allocation failed"**: Insufficient system resources

## Maintenance

### Regular Maintenance Tasks

#### Daily
- Monitor system status via web interface
- Check for any error messages in logs
- Verify displays are functioning correctly

#### Weekly
```bash
# Check system health
./health_check.sh

# Review log files
tail -100 logs/becaticker.log | grep ERROR

# Check disk space
df -h

# Monitor system temperature
vcgencmd measure_temp
```

#### Monthly
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Backup configuration
cp config.json backups/config-$(date +%Y%m%d).json

# Check for BecaTicker updates
git fetch
git log HEAD..origin/main --oneline

# Clean up old logs (if not using logrotate)
find logs/ -name "*.log.*" -mtime +30 -delete
```

#### Quarterly
- Full system backup
- Hardware inspection (connections, cooling)
- Performance review and optimization
- Security audit (password changes, access review)

### Backup and Recovery

#### Configuration Backup
```bash
# Backup all configuration
tar -czf becaticker-backup-$(date +%Y%m%d).tar.gz \
    config.json images/ logs/

# Restore configuration
tar -xzf becaticker-backup-YYYYMMDD.tar.gz
sudo systemctl restart becaticker
```

#### Full System Backup
```bash
# Create system image (run from another machine)
sudo dd if=/dev/sdX of=becaticker-system-backup.img bs=4M status=progress

# Or use rsync for incremental backups
rsync -av --exclude='/proc/*' --exclude='/sys/*' \
    pi@becaticker-ip:/ /backup/becaticker/
```

#### Disaster Recovery
1. **Hardware Failure**: Replace hardware, restore from backup
2. **SD Card Corruption**: Flash new image, restore configuration
3. **Software Issues**: Reinstall via `deploy.sh`, restore config
4. **Configuration Loss**: Restore from backup, verify settings

### Performance Optimization

#### System Optimization
```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable wifi-country

# Optimize GPU memory split
echo "gpu_mem=64" | sudo tee -a /boot/config.txt

# Reduce logging if needed
sudo nano /etc/rsyslog.conf
```

#### Display Optimization
- **Brightness**: Lower brightness reduces power and heat
- **Refresh Rate**: Adjust based on content type
- **Color Depth**: Reduce if experiencing performance issues
- **Text Speed**: Optimize for readability vs. content volume

### Scaling Considerations

#### Adding More Panels
- Update `chain_length` in matrix_options
- Ensure adequate power supply capacity
- Test with incremental additions
- Monitor voltage drop across chain

#### Multiple Installations
- Standardize configuration templates
- Use central configuration management
- Implement monitoring dashboard
- Consider automated deployment tools

## Security

### Security Best Practices

#### Access Control
- **Change default password** immediately after installation
- Use strong passwords (minimum 12 characters)
- Limit web interface access via firewall
- Consider VPN access for remote management

#### Network Security
```bash
# Configure firewall
sudo ufw enable
sudo ufw allow 22    # SSH
sudo ufw allow 5000  # Web interface (restrict source if possible)

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon

# Change default SSH port
sudo nano /etc/ssh/sshd_config
```

#### Application Security
- Web interface uses session-based authentication
- API endpoints require authentication
- Configuration files protected by filesystem permissions
- Logs contain no sensitive information

#### System Hardening
```bash
# Update system regularly
sudo apt update && sudo apt upgrade

# Remove unnecessary packages
sudo apt autoremove

# Configure automatic security updates
sudo dpkg-reconfigure unattended-upgrades
```

### Monitoring Security

#### Log Monitoring
```bash
# Monitor authentication attempts
grep "authentication" logs/becaticker.log

# Check system logs for intrusion attempts
sudo journalctl -u ssh -f
```

#### Regular Security Tasks
- Review user access logs monthly
- Update passwords quarterly
- Monitor for unusual network activity
- Keep system and dependencies updated

## Performance

### System Requirements

#### Minimum Requirements
- Raspberry Pi 3B+ or newer
- 2GB RAM
- Class 10 MicroSD card (16GB)
- 5V 10A power supply

#### Recommended Specifications
- Raspberry Pi 4 (4GB RAM)
- Class 10 MicroSD card (32GB+)
- 5V 20A power supply
- Active cooling (fan + heatsink)

### Performance Metrics

#### Typical Performance
- **CPU Usage**: 15-30% average
- **Memory Usage**: 200-400MB
- **Display Refresh**: 60 FPS
- **Web Response**: <100ms
- **Calendar Update**: Every 30 minutes

#### Performance Monitoring
```bash
# System resources
htop
free -h
df -h

# Temperature monitoring
watch vcgencmd measure_temp

# Network performance
iftop

# Application performance
tail -f logs/becaticker.log | grep "Update complete"
```

### Optimization Tips

#### Display Performance
- Reduce `brightness` to minimum acceptable level
- Optimize `scroll_speed` for content and readability
- Use solid colors instead of gradients when possible
- Minimize frequent color changes

#### System Performance
- Use fast MicroSD card (Class 10 minimum, A1 preferred)
- Enable GPU split: `gpu_mem=64`
- Disable unnecessary services
- Use wired network connection when possible

#### Web Interface Performance
- Minimize simultaneous web sessions
- Use efficient calendar update intervals
- Optimize image sizes for picture viewer
- Consider caching for frequently accessed content

## File Structure

```
becaticker/
├── becaticker.py              # Main application (3,350+ lines)
│   ├── Config class           # Configuration management
│   ├── CalendarManager        # iCal integration
│   ├── PictureViewer         # Image display management
│   ├── TextDisplay           # Chain 1 text rendering
│   ├── ClockDisplay          # Chain 2 clock/picture rendering
│   ├── UserManager           # Authentication system
│   └── BecaTicker            # Main application controller
│
├── config.json               # System configuration
│   ├── matrix_options        # Hardware settings
│   ├── display_settings      # Visual appearance
│   ├── calendar_urls         # Event sources
│   └── user_credentials      # Authentication data
│
├── requirements.txt          # Python dependencies
├── becaticker.service       # Systemd service definition
├── deploy.sh               # Production deployment script
├── setup.sh                # Development setup script
├── health_check.sh         # System diagnostics
├── run.sh                  # Manual execution script
├── README.md               # This documentation
│
├── templates/              # Web interface templates
│   ├── index.html         # Main dashboard
│   └── login.html         # Authentication page
│
├── images/                 # Picture viewer assets
│   └── (user uploaded images)
│
├── logs/                   # Application logs
│   └── becaticker.log     # Main log file
│
├── hzeller/                # RGB matrix library (git submodule)
│   ├── lib/               # Core matrix library
│   ├── bindings/python/   # Python interface
│   └── examples/          # Reference implementations
│
└── .git/                   # Git repository data
    └── modules/hzeller    # Submodule reference
```

### Key Configuration Files

#### `config.json` Structure
```json
{
  "department_name": "Display department name",
  "scrolling_messages": ["Array of text messages"],
  "calendar_urls": ["Array of iCal URLs"],
  "web_port": 5000,
  "matrix_options": {
    "brightness": 40,
    "chain_length": 5,
    "parallel": 2,
    "cols": 64,
    "rows": 64,
    "gpio_slowdown": 4
  },
  "display_settings": {
    "scroll_speed": 0.5,
    "text_color": [255, 255, 255],
    "background_color": [0, 0, 0],
    "calendar_refresh_minutes": 30
  },
  "second_display": {
    "enabled": true,
    "type": "clock",
    "settings": {
      "show_date": true,
      "date_color": [128, 180, 255],
      "date_format": "%Y-%m-%d"
    }
  },
  "users": {
    "admin": {
      "password_hash": "hashed_password",
      "role": "admin"
    }
  }
}
```

#### `becaticker.service` Configuration
```ini
[Unit]
Description=BecaTicker LED Matrix Display Service
After=network.target network-online.target
Wants=network-online.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=10
User=root
WorkingDirectory=/home/becaticker/becaticker
Environment=PATH=/home/becaticker/becaticker/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/home/becaticker/becaticker/venv/bin/python /home/becaticker/becaticker/becaticker.py
StandardOutput=journal
StandardError=journal
SyslogIdentifier=becaticker

[Install]
WantedBy=multi-user.target
```

## Technical Specifications

### Hardware Specifications

#### Supported Panels
- **Type**: 64×64 RGB LED panels
- **Interface**: HUB75 connector
- **Voltage**: 5V DC
- **Current**: ~2-8A per panel (depends on brightness and content)
- **Pixel Pitch**: Typically 2.5mm-4mm
- **Compatibility**: Most standard HUB75 panels

#### Raspberry Pi Requirements
- **Models**: Pi 3B+, Pi 4 (all variants)
- **GPIO**: Full 40-pin header required
- **Power**: 5V 3A minimum for Pi alone
- **Cooling**: Recommended for continuous operation
- **Storage**: 16GB minimum, 32GB+ recommended

#### Interface Board
- **Primary**: Adafruit RGB Matrix HAT/Bonnet
- **Alternative**: Compatible HUB75 interface boards
- **Features**: Level shifting, proper termination, power distribution
- **GPIO Mapping**: Standard RGB matrix pinout

### Software Specifications

#### Operating System
- **Base**: Raspberry Pi OS (Bullseye or newer)
- **Architecture**: ARM64 preferred, ARM32 compatible
- **Kernel**: Standard Raspberry Pi kernel
- **Services**: Systemd-based service management

#### Python Environment
- **Version**: Python 3.9+ required
- **Dependencies**: See requirements.txt
- **Virtual Environment**: Isolated package installation
- **Performance**: Optimized for real-time display updates

#### Network Requirements
- **Connectivity**: Ethernet recommended, WiFi supported
- **Bandwidth**: Minimal (calendar updates, web interface)
- **Protocols**: HTTP/HTTPS for web interface and calendar
- **Firewall**: Configurable ports (default 5000)

### Display Specifications

#### Chain 1 (Text Display)
- **Resolution**: 320×64 pixels (5 panels × 64×64)
- **Content**: Scrolling text, calendar events, announcements
- **Update Rate**: Real-time text scrolling
- **Color Depth**: 24-bit RGB
- **Typography**: Bitmap fonts, multiple sizes

#### Chain 2 (Clock/Pictures)
- **Resolution**: 128×128 pixels (2×2 panels × 64×64)
- **Content**: Analog clock, digital information, pictures
- **Update Rate**: 1 Hz for clock, configurable for pictures
- **Features**: Multiple clock styles, slideshow capability
- **Image Formats**: JPEG, PNG, GIF

### Performance Specifications

#### Real-time Requirements
- **Display Refresh**: 60 FPS minimum
- **Text Scrolling**: Smooth animation
- **Clock Updates**: Sub-second precision
- **Web Interface**: <200ms response time
- **Calendar Sync**: 30-minute intervals (configurable)

#### Resource Usage
- **CPU**: 15-30% average load
- **Memory**: 200-400MB RAM usage
- **Storage**: <1GB base installation
- **Network**: <1MB/hour for calendar updates
- **Power**: 2-3A base system + panel consumption

### Integration Specifications

#### Calendar Integration
- **Formats**: iCal (.ics), ICS URLs
- **Protocols**: HTTP, HTTPS
- **Authentication**: Basic auth, bearer tokens
- **Filtering**: Event type, date range, keywords
- **Caching**: Local event storage with refresh

#### API Specifications
- **Protocol**: RESTful HTTP API
- **Authentication**: Session-based, basic auth
- **Format**: JSON request/response
- **Rate Limiting**: Built-in protection
- **Documentation**: OpenAPI compatible

#### Web Interface
- **Framework**: Flask with Jinja2 templates
- **Compatibility**: Modern browsers (Chrome, Firefox, Safari, Edge)
- **Responsive**: Desktop and mobile optimized
- **Security**: CSRF protection, session management
- **Real-time**: JavaScript-based status updates

---

## Handover Checklist

### For System Administrator
- [ ] Review hardware setup and wiring diagrams
- [ ] Understand power requirements and safety considerations
- [ ] Familiarize with web interface and configuration options
- [ ] Test backup and recovery procedures
- [ ] Set up monitoring and maintenance schedule
- [ ] Change default passwords and review security settings

### For Developer
- [ ] Review code architecture and main classes
- [ ] Understand display rendering pipeline
- [ ] Set up development environment
- [ ] Review API documentation and integration points
- [ ] Understand configuration management system
- [ ] Review testing and debugging procedures

### For End User
- [ ] Learn web interface navigation
- [ ] Understand how to update messages and settings
- [ ] Know how to upload and manage pictures
- [ ] Understand calendar integration setup
- [ ] Know basic troubleshooting steps
- [ ] Have contact information for technical support

---

This documentation provides comprehensive coverage of the BecaTicker system for successful handover and ongoing maintenance. For additional support or questions, refer to the project repository or contact the development team.

