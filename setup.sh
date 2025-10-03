#!/bin/bash

echo "🔧 Setting up BecaTicker on Raspberry Pi..."
echo "==========================================="

# Configure the pi to work with the LED modules
echo "🔌 Configuring Raspberry Pi for LED matrices..."

## Switch off the raspberry pi sound dtparam
sudo sed -i 's/^dtparam=audio=on/dtparam=audio=off/' /boot/firmware/config.txt || \
sudo sed -i 's/^dtparam=audio=on/dtparam=audio=off/' /boot/config.txt

## Disable w1-gpio on the pi
sudo sed -i 's/^dtoverlay=w1-gpio/#dtoverlay=w1-gpio/' /boot/firmware/config.txt || \
sudo sed -i 's/^dtoverlay=w1-gpio/#dtoverlay=w1-gpio/' /boot/config.txt

## Install required system packages
echo "📦 Installing system packages..."
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-full git build-essential \
    libgraphicsmagick++-dev libwebp-dev libjpeg-dev libgif-dev \
    python3-dev cython3

## Remove unneeded packages to free up resources
echo "🗑️  Removing unnecessary packages..."
sudo apt-get remove bluez bluez-firmware pi-bluetooth triggerhappy pigpio -y
sudo apt-get autoremove -y

# Set up this project
echo "⚙️  Setting up BecaTicker project..."

## Initialize git submodules
git submodule update --init --recursive

## Create Python virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

## Upgrade pip and install build tools
pip install --upgrade pip setuptools wheel

## Try to build the RGB matrix library
echo "🔨 Building RGB Matrix library..."
cd hzeller
make build-python PYTHON=$(which python3) || {
    echo "⚠️  Build failed, trying alternative build..."
    make clean
    make PYTHON=$(which python3)
}
cd ..

## Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt
pip install -r hzeller/bindings/python/requirements.txt

## Create logs directory
mkdir -p logs

## Set `becaticker.sh` to be run as root after startup
echo "🔄 Setting up systemd service..."
sudo cp becaticker.service /etc/systemd/system/becaticker.service
sudo systemctl enable becaticker.service
sudo systemctl daemon-reload

echo ""
echo "✅ Setup complete!"
echo "📋 Next steps:"
echo "   1. Reboot your Raspberry Pi: sudo reboot"
echo "   2. After reboot, start manually: sudo ./start_becaticker.sh"
echo "   3. Or let the service start automatically"
echo "   4. Access web interface at http://$(hostname -I | awk '{print $1}'):5000"
echo ""