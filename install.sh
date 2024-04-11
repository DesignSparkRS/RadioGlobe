#! /usr/bin/bash

# Install all dependencies and setup radioglobe service to run under default user

sudo apt install vlc-bin vlc-plugin-base
# sudo apt install vlc pulseaudio python3-pip python3-smbus python3-dev python3-rpi.gpio

# Create python virtual environment
echo "Creating virtual environment..."
python -m venv venv
source ./venv/bin/activate

# Install python dependencies
pip install spidev
pip install smbus

# Bullseye only
#pip install RPi.GPIO
# Bookworm compatibility with RPi.GPIO
pip install lgpio
pip install rpi-lgpio
pip install python-vlc
pip3 install https://github.com/pl31/python-liquidcrystal_i2c/archive/master.zip
#pip3 install python-vlc

# Set paths according to username
sed -i "s/USER/${USER}/g" services/*.service
sudo cp services/*.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl enable radioglobe.service
sudo systemctl start radioglobe.service
