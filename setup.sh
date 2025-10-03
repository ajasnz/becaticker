#!/bin/bash

# Configure the pi to work with the LED modules

## Switch off the raspberry pi sound dtparam
sudo sed -i 's/^dtparam=audio=on/dtparam=audio=off/' /boot/firmware/config.txt

## Disable w1-gpio on the pi
sudo sed -i 's/^dtoverlay=w1-gpio/#dtoverlay=w1-gpio/' /boot/firmware/config.txt

## Remove unneeded packages
sudo apt-get remove bluez bluez-firmware pi-bluetooth triggerhappy pigpio -y


# Set up this project

## Initialize git submodules
git submodule update --init --recursive

## Set `becaticker.sh` to be run as root after startup
sudo cp becaticker.service /etc/systemd/system/becaticker.service
sudo systemctl enable becaticker.service
sudo systemctl daemon-reload