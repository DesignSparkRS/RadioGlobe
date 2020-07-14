#! /bin/sh
pip3 install https://github.com/pl31/python-liquidcrystal_i2c/archive/master.zip
pip3 install python-vlc
sudo apt install vlc pulseaudio
sudo cp services/*.service /etc/systemd/system
sudo systemctl daemon-reload
sudo systemctl start radioglobe.service
sudo systemctl enable radioglobe.service
