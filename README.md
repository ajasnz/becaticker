# 🎯 BecaTicker - LED Matrix Display Controller

A comprehensive dual-chain RGB LED matrix display system designed for Raspberry Pi, featuring department information display, calendar integration, and arcade gaming support.

## ✨ Features

- **Dual Chain Architecture**: Two independent LED matrix chains for different purposes
- **Web Interface**: Modern responsive web interface for configuration
- **Calendar Integration**: ICS calendar feed support for displaying upcoming events
- **Arcade Mode**: Integration with RetroPie for gaming on the secondary display
- **Real-time Clock**: Beautiful analog clock display
- **Customizable Messages**: Scrolling text messages configurable via web interface
- **Department Branding**: Customizable department name display
- **Auto-startup**: Systemd service for automatic startup on boot

## 🖥️ Display Configuration

### Chain 1: Text Display (4x1 - 256x64 pixels)
A horizontal chain of four 64x64 panels displaying:
1. **Department Name** - Static text at the top
2. **Scrolling Messages** - Customizable rotating messages
3. **Calendar Events** - Upcoming events from ICS feeds

### Chain 2: Clock/Arcade Display (2x2 - 128x128 pixels) 
A square arrangement of four 64x64 panels featuring:
- **Analog Clock** - Real-time clock display (default mode)
- **Arcade Gaming** - RetroPie integration for retro gaming

## 🚀 Quick Start

### Prerequisites
- Raspberry Pi (3B+ or 4 recommended)
- Two chains of 64x64 RGB LED matrix panels
- Adafruit RGB Matrix HAT or compatible
- MicroSD card (32GB+ recommended)
- Reliable 5V power supply

### Installation

1. **Clone the repository with submodules:**
   ```bash
   git clone --recurse-submodules https://github.com/ajasnz/becaticker.git
   cd becaticker
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   sudo ./setup.sh
   ```

3. **Reboot to apply system changes:**
   ```bash
   sudo reboot
   ```

4. **Start the application:**
   ```bash
   chmod +x start_becaticker.sh
   sudo ./start_becaticker.sh
   ```

## 🌐 Web Interface

After starting the application, access the web interface at:
- **Local**: http://localhost:5000
- **Network**: http://[your-pi-ip]:5000

### Web Interface Features
- **Live Status Dashboard** - System status and event counts
- **Department Configuration** - Set department name
- **Message Management** - Add/remove scrolling messages
- **Calendar Setup** - Configure ICS calendar feeds
- **Event Preview** - View upcoming calendar events
- **Arcade Controls** - Start/stop arcade mode
- **Configuration Export/Import** - Backup and restore settings

## ⚙️ Configuration

The system uses a JSON configuration file (`config.json`) with the following structure:

```json
{
  "department_name": "ENGINEERING",
  "scrolling_messages": [
    "Welcome to our department!",
    "Safety first - always wear your PPE",
    "Team meeting every Thursday at 2 PM"
  ],
  "calendar_urls": [
    "https://example.com/calendar.ics"
  ],
  "web_port": 5000,
  "matrix_options": {
    "chain1": {
      "rows": 64,
      "cols": 64,
      "chain_length": 4,
      "parallel": 1,
      "brightness": 75,
      "gpio_mapping": "adafruit-hat"
    },
    "chain2": {
      "rows": 64,
      "cols": 64,
      "chain_length": 4,
      "parallel": 1,
      "brightness": 75,
      "gpio_mapping": "adafruit-hat"
    }
  },
  "display_settings": {
    "text_color": [255, 255, 255],
    "clock_color": [0, 255, 0],
    "background_color": [0, 0, 0],
    "scroll_speed": 0.05,
    "calendar_refresh_minutes": 30
  },
  "arcade_mode": {
    "enabled": true,
    "trigger_command": "/usr/bin/emulationstation"
  }
}
```

### Key Configuration Options

| Setting                    | Description                  | Default         |
| -------------------------- | ---------------------------- | --------------- |
| `department_name`          | Static text displayed at top | "DEPARTMENT"    |
| `scrolling_messages`       | Array of rotating messages   | Sample messages |
| `calendar_urls`            | ICS calendar feed URLs       | Empty array     |
| `web_port`                 | Web interface port           | 5000            |
| `brightness`               | LED brightness (1-100)       | 75              |
| `scroll_speed`             | Message scroll speed         | 0.05            |
| `calendar_refresh_minutes` | Calendar update interval     | 30              |

## 🎮 Arcade Mode

BecaTicker integrates with RetroPie to transform the clock display into a gaming screen:

1. **Install RetroPie** on your Raspberry Pi
2. **Enable arcade mode** in the configuration
3. **Use the web interface** to start/stop arcade mode
4. **The text display continues** to operate normally during gaming

### Arcade Mode Controls
- Start arcade mode via web interface
- Automatically launches EmulationStation
- Clock display is suspended during gaming
- Return to clock when exiting games

## 📅 Calendar Integration

### Supported Calendar Formats
- **ICS/iCal files** - Standard calendar format
- **Google Calendar** - Use the public ICS URL
- **Outlook Calendar** - Export as ICS
- **Other services** - Any service providing ICS feeds

### Adding Calendars
1. **Get the ICS URL** from your calendar service
2. **Add via web interface** or edit `config.json`
3. **Events automatically refresh** every 30 minutes
4. **Only future events** within 7 days are shown

### Example Calendar URLs
```json
"calendar_urls": [
  "https://calendar.google.com/calendar/ical/your-calendar-id/public/basic.ics",
  "https://outlook.office365.com/owa/calendar/your-calendar/reachable/public/basic.ics"
]
```

## 🔧 Hardware Setup

### Wiring
- Follow the [rpi-rgb-led-matrix wiring guide](https://github.com/hzeller/rpi-rgb-led-matrix/blob/master/wiring.md)
- Use quality jumper wires and ensure solid connections
- Consider using the Adafruit RGB Matrix HAT for reliability

### Power Requirements
- Each 64x64 panel can draw up to 8A at full brightness
- Use a high-quality 5V power supply (20A+ recommended for 8 panels)
- Consider power injection for long chains

### Panel Layout
```
Chain 1 (Text): [P1][P2][P3][P4]
Chain 2 (Clock): [P5][P6]
                 [P7][P8]
```

## 🔄 System Service

The application runs as a systemd service for automatic startup:

```bash
# Check service status
sudo systemctl status becaticker

# Start/stop service
sudo systemctl start becaticker
sudo systemctl stop becaticker

# Enable/disable auto-start
sudo systemctl enable becaticker
sudo systemctl disable becaticker

# View logs
sudo journalctl -u becaticker -f
```

## 📝 Logging

Application logs are stored in:
- **System logs**: `sudo journalctl -u becaticker`
- **Application logs**: `becaticker.log`
- **Startup logs**: `logs/becaticker_YYYYMMDD_HHMMSS.log`

## 🛠️ Troubleshooting

### Common Issues

1. **"Permission denied" errors**
   - Run with `sudo` (required for GPIO access)
   - Check file permissions: `chmod +x becaticker.sh`

2. **Matrix not displaying**
   - Verify wiring connections
   - Check power supply capacity
   - Review `gpio_mapping` setting in config

3. **Web interface not accessible**
   - Check if port 5000 is blocked by firewall
   - Verify the Pi's IP address
   - Ensure the service is running

4. **Calendar events not showing**
   - Verify ICS URL is accessible
   - Check internet connection
   - Review logs for HTTP errors

5. **Arcade mode not working**
   - Ensure RetroPie is installed
   - Check `trigger_command` path
   - Verify arcade mode is enabled in config

### Debug Mode
```bash
sudo python3 becaticker.py --log-level DEBUG
```

## 🚀 Performance Optimization

### For better performance:
- Use faster SD card (Class 10, U3)
- Disable unnecessary services
- Reduce LED brightness if power is limited
- Use Pi 4 for better performance with arcade mode

### Memory optimization:
```bash
# Add to /boot/config.txt
gpu_mem=16
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature-name`
5. Submit a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Henner Zeller** - [rpi-rgb-led-matrix library](https://github.com/hzeller/rpi-rgb-led-matrix)
- **RetroPie Project** - [RetroPie gaming platform](https://retropie.org.uk/)
- **Flask Team** - [Flask web framework](https://flask.palletsprojects.com/)

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section above
- Review the system logs for error messages

---

**Made with ❤️ by the Engineering Team**