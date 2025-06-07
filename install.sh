#! /usr/bin/bash

# Install all dependencies and setup radioglobe service to run under radioglobe user
# The script assumes the repo is cloned to the radioglobe home directory
# and it is executed from within the ~/RadioGlobe dir

# sudo apt install vlc-bin vlc-plugin-base python3-venv python3-dev pulseaudio-module-bluetooth
# sudo apt install vlc pulseaudio python3-pip python3-smbus python3-dev python3-rpi.gpio
echo "Installing OS dependencies..."
sudo apt install vlc-bin vlc-plugin-base python3-dev pulseaudio-module-bluetooth

# Create python virtual environment and activate it so python packages can be installed in it
echo "Creating virtual environment..."
export RADIOGLOBE_DIR=/opt/radioglobe
sudo mkdir $RADIOGLOBE_DIR
sudo chown radioglobe:radioglobe $RADIOGLOBE_DIR
python -m venv $RADIOGLOBE_DIR/venv
source $RADIOGLOBE_DIR/venv/bin/activate
cp requirements.txt $RADIOGLOBE_DIR/
pip install -r $RADIOGLOBE_DIR/requirements.txt

# Check python dependencies are correctly installed in venv
echo "Checking python venv..."
if [[ -z "$VIRTUAL_ENV" ]]; then
  echo "❌ Please activate your virtual environment first."
  exit 1
fi

echo "🔍 Checking Python packages in requirements.txt against current venv..."

while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue

  # Extract package name
  if [[ "$line" =~ @\  ]]; then
    # Handle VCS entries like: package @ git+https://...
    pkg_name=$(echo "$line" | cut -d '@' -f 1 | xargs)
  else
    # Handle regular entries like: package==version
    pkg_name=$(echo "$line" | cut -d '=' -f 1 | cut -d '<' -f 1 | cut -d '>' -f 1 | xargs)
  fi

  # Check if the package is installed
  pip show "$pkg_name" > /dev/null 2>&1
  if [[ $? -eq 0 ]]; then
    echo "✅ $pkg_name is installed"
  else
    echo "❌ $pkg_name is NOT installed"
  fi
done < $RADIOGLOBE_DIR/requirements.txt

# Replaced by above to put dependencies into venv not OS - Bullseye no longer supported
# Install python dependencies
# pip install spidev
# pip install smbus
# pip install python-vlc
# pip install https://github.com/pl31/python-liquidcrystal_i2c/archive/master.zip

# Install appropriate GPIO support
# source /etc/os-release
# echo "$VERSION_CODENAME"
# case $VERSION_CODENAME in
#     bullseye)
#     # Legacy support
#     pip install RPi.GPIO
#     ;;
#     bookworm)
#     # Bookworm compatibility with RPi.GPIO
#     pip install lgpio
#     pip install rpi-lgpio
#     ;;
#     *)
#     echo "Debian version unknown"
#     exit
#     ;;
# esac

# Copy files to working dir
echo "Copying scripts to /opt/radioglobe..."
cp -r radioglobe/* /opt/radioglobe/

# Copy stations file
echo "Copying stations file..."
cp stations/stations.json /opt/radioglobe/

# Remove any old radioglobe service
echo "Stopping any existing services..."
FILE=/etc/systemd/system/radioglobe.service
if [[ -f "$FILE" ]]; then
    sudo systemctl stop radioglobe.service
    sudo systemctl disable radioglobe.service
    sudo systemctl daemon-reload
    sudo rm $FILE
fi

# Set paths according to username
#sed -i "s/USER/${USER}/g" services/radioglobe.service
# Start radioglobe as the default user, NOT root so pulseaudio can manage audio
echo "Installing service units..."
sudo cp services/radioglobe.service /etc/systemd/user/
systemctl --user daemon-reload
systemctl --user enable pulseaudio
systemctl --user enable radioglobe.service
systemctl --user start pulseaudio

sudo reboot
