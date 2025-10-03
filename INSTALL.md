# BecaTicker Installation Guide

## Quick Installation Steps

1. **Prepare your Raspberry Pi**
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install git python3 python3-pip -y
   ```

2. **Clone this repository**
   ```bash
   git clone --recurse-submodules https://github.com/your-username/becaticker.git
   cd becaticker
   ```

3. **Run setup**
   ```bash
   chmod +x setup.sh start_becaticker.sh
   sudo ./setup.sh
   sudo reboot
   ```

4. **Start the application**
   ```bash
   sudo ./start_becaticker.sh
   ```

5. **Access web interface**
   - Open browser to http://your-pi-ip:5000
   - Configure your settings
   - Enjoy your LED display!

## Hardware Requirements

- Raspberry Pi 3B+ or 4
- 8x 64x64 RGB LED matrix panels
- Adafruit RGB Matrix HAT
- 5V 20A+ power supply
- Quality jumper wires

## Support

See README.md for detailed documentation and troubleshooting.