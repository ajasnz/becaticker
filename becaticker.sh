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

## Make sure we have python3, venv, and git
sudo apt-get install python3 python3-venv python3-full git build-essential -y

## Pull the latest code from the repository
git pull origin main

## Make sure the submodules are up to date
git submodule update --init --recursive

## Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

## Activate virtual environment
source venv/bin/activate

## Upgrade pip in virtual environment
pip install --upgrade pip

## Compile the LED matrix library
cd hzeller
make build-python PYTHON=$(which python3)
cd ..

## Install requirements in virtual environment
pip install -r requirements.txt
pip install -r hzeller/bindings/python/requirements.txt

# Run the main application with sudo but keep the virtual environment
sudo venv/bin/python becaticker.py