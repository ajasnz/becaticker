# BecaTicker - LED Matrix Display

Simple dual-chain RGB LED matrix display for Raspberry Pi.

## What it does

- **Chain 1**: 5×1 panels (256×64) - scrolling text and calendar events
- **Chain 2**: 2×2 panels (128×128) - analog clock
- **Web interface**: configure everything via browser

## Quick Setup

```bash
git clone --recurse-submodules https://github.com/ajasnz/becaticker.git
cd becaticker
sudo ./setup.sh
```

Access web interface: `http://[pi-ip]:5000`

## Hardware Needed

- Raspberry Pi 3B+/4
- 8× 64×64 RGB LED panels (HUB75)
- Adafruit RGB Matrix HAT
- 5V 20A+ power supply

## Files

- `becaticker.py` - main application
- `setup.sh` - installation
- `config.json` - settings
- `templates/index.html` - web interface

## Service Commands

```bash
sudo systemctl start becaticker    # start
sudo systemctl status becaticker   # check status
sudo journalctl -u becaticker -f   # view logs
```

That's it.