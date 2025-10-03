#!/bin/bash

# BecaTicker - LED Matrix Display Controller
# This script handles the setup and execution of the BecaTicker application.

# Set the working directory to the script's location
cd "$(dirname "$0")"

# Prepare the system

## Wait for network connectivity
while ! ping -c 1 -W 1 google.com; do
    echo "Waiting for network..."
    sleep 1
done

## Update package lists and upgrade installed packages
sudo apt-get update
sudo apt-get upgrade -y

## Make sure we have python3, pip, and git
sudo apt-get install python3 python3-pip git -y
sudo pip3 install --upgrade pip

## Pull the latest code from the repository
git pull origin main

## Make sure the submodules are up to date
git submodule update --init --recursive

## Compile the LED matrix library
cd hzeller
make build-python3 
cd ..


## Install requirements
sudo pip3 install -r requirements.txt
sudo pip3 install -r hzeller/bindings/python/requirements.txt

# Run the main application
sudo python3 becaticker.py