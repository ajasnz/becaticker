# BecaTicker - LED Matrix Display Controller

Professional RGB LED matrix display system for Raspberry Pi featuring dual-chain configuration with web-based management.

## Features

- **Chain 1**: 5×1 panels (320×64) - scrolling text, messages, and calendar events
- **Chain 2**: 2×2 panels (128×128) - analog clock and picture viewer
- **Web Interface**: Complete configuration and control via browser
- **Calendar Integration**: iCal/ICS calendar support with event display
- **Picture Display**: Image viewing capabilities with slideshow mode
- **User Management**: Secure login system with admin controls
- **Production Ready**: Systemd service, logging, health monitoring

## Physical Panel Layout

```
                                   | (2)1 | (2)4 |
| (1)4 | (1)3 | (1)2 | (1)1 | (1)0 | (2)2 | (2)3 |
```

## Quick Production Deployment

```bash
git clone --recurse-submodules https://github.com/ajasnz/becaticker.git
cd becaticker
sudo ./deploy.sh
```

Access web interface: `http://[raspberry-pi-ip]:5000`
Default login: `admin` / `admin` (⚠️ **Change immediately!**)

## Hardware Requirements

- Raspberry Pi 3B+ or 4 (recommended: 4GB+ RAM)
- 7× 64×64 RGB LED panels (HUB75 connector)
- Adafruit RGB Matrix HAT or compatible
- 5V 20A+ power supply (adjust based on panel count)
- MicroSD card (32GB+ recommended)

## Development Setup

For development or testing:

```bash
git clone --recurse-submodules https://github.com/ajasnz/becaticker.git
cd becaticker
sudo ./setup.sh
```

## Configuration

Edit `config.json` or use the web interface to configure:
- Display settings (colors, brightness, text speed)
- Calendar URLs (iCal/ICS format)
- Network and web interface settings
- User management

## System Management

```bash
# Service control
sudo systemctl start becaticker     # Start service
sudo systemctl stop becaticker      # Stop service
sudo systemctl restart becaticker   # Restart service
sudo systemctl status becaticker    # Check status

# Monitoring
sudo journalctl -u becaticker -f     # View live logs
tail -f logs/becaticker.log          # View application logs
./health_check.sh                    # Run health check

# Updates
git pull                             # Update code
sudo systemctl restart becaticker   # Restart service
```

## Security Considerations

For production deployment:
1. **Change default password** immediately via web interface
2. Configure firewall to restrict web interface access
3. Use SSL/TLS proxy if accessing over public networks
4. Regularly monitor log files for unusual activity
5. Keep system and dependencies updated

## File Structure

```
becaticker/
├── becaticker.py          # Main application
├── deploy.sh             # Production deployment script
├── setup.sh              # Development setup script
├── health_check.sh       # System health check
├── requirements.txt      # Python dependencies
├── config.json           # Configuration file
├── becaticker.service    # Systemd service definition
├── logs/                 # Application logs
├── images/               # Picture viewer images
├── templates/            # Web interface templates
└── hzeller/              # RGB matrix library (submodule)
```

## API Endpoints

- `GET /api/status` - System status
- `GET /api/config` - Current configuration
- `POST /api/config` - Update configuration
- `GET /api/pictures/status` - Picture viewer status
- `POST /api/pictures/start` - Start picture mode
- `POST /api/pictures/stop` - Stop picture mode

## Troubleshooting

**Service won't start:**
```bash
sudo journalctl -u becaticker -n 50  # Check logs
./health_check.sh                    # Run diagnostics
```

**Web interface not accessible:**
- Check firewall settings
- Verify service is running: `sudo systemctl status becaticker`
- Check network configuration

**Display issues:**
- Verify hardware connections
- Check power supply capacity
- Review GPIO configuration in code

## Support

For issues and feature requests, please use the project's issue tracker.

## License

See LICENSE file for details.

