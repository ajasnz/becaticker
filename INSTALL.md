# BecaTicker Installation Guide

## Quick Installation Steps

1. **Prepare your Raspberry Pi**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install git python3 python3-venv python3-full build-essential -y
   ```

2. **Clone this repository**
   ```bash
   git clone --recurse-submodules https://github.com/ajasnz/becaticker.git
   cd becaticker
   ```

3. **Run setup (handles virtual environment automatically)**
   ```bash
   chmod +x setup.sh start_becaticker.sh troubleshoot.sh
   sudo ./setup.sh
   ```

4. **Reboot to apply hardware changes**
   ```bash
   sudo reboot
   ```

5. **Start the application**
   ```bash
   sudo ./start_becaticker.sh
   ```

6. **Access web interface**
   - Open browser to http://your-pi-ip:5000
   - Configure your settings
   - Enjoy your LED display!

## Troubleshooting

If you encounter issues, run the troubleshooting script:
```bash
./troubleshoot.sh
```

Common fixes:
- **Build errors**: Install build-essential and python3-dev packages
- **Permission issues**: Make sure scripts are executable with `chmod +x`
- **Python environment**: The setup now uses virtual environments to avoid conflicts
- **Service issues**: Check with `sudo systemctl status becaticker`

## Hardware Requirements

- Raspberry Pi 3B+ or 4 (Pi 4 recommended)
- 8x 64x64 RGB LED matrix panels (HUB75 connector)
- Adafruit RGB Matrix HAT or Bonnet
- 5V 20A+ power supply (high quality required)
- Quality jumper wires and breadboard connections
- MicroSD card (32GB+ Class 10 recommended)

## Key Changes for Modern Raspberry Pi OS

This installation now properly handles:
- ✅ **Virtual environments** (required by modern Python)
- ✅ **Proper build dependencies** for RGB matrix library
- ✅ **Systemd service configuration** with virtual environment
- ✅ **Hardware configuration** for both old and new Pi configs
- ✅ **Troubleshooting tools** for common issues

## Support

- Run `./troubleshoot.sh` for diagnostic information
- Check `sudo journalctl -u becaticker -f` for service logs
- See README.md for detailed documentation