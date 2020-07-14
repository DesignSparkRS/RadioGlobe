# Radioglobe

First, install Raspberry Pi OS (Buster lite) onto a microSD card.

You will need to perform setup using SSH, or with a mouse, keyboard and monitor.  To use SSH without needing to
enable it in the settings menu, just place an empty file named 'ssh' in the 'BOOT' volume:
1. Insert the microSD card containing the Raspberry Pi OS installation into a Mac or PC.
2. Open the 'BOOT' volume in My Computer (Windows), Files (Ubuntu) or Finder (macOS).
3. Create a new text file and name it 'ssh'.  On Windows, don't forget to remove the file extension (.txt).
4. Alternatively in Linux or macOS cd to the 'BOOT' volume and run ```touch ssh```
5. Unmount the microSD card and insert it into the Raspberry Pi.
6. Plug the Raspberry Pi into your router using an Ethernet cable and power it on.
7. Once it has booted, open your SSH compatible terminal program (PuTTy on Windows, or pretty much anything in macOS or
   Linux) and run ```ssh raspberrypi.local``` (assuming that is the hostname of the Raspberry Pi of course).

## Installation
From an SSH terminal:
1. Run ```sudo raspi-config```
2. In 'Network Options', enter the details (SSID and password) for your wi-fi network if you want to.
3. In 'Interfacing Options' enable SPI and I2C.
4. Run ```mkdir ~/work && cd ~/work```  (You can actually put it in a different folder, but you'll need to perform an
   additional step if you do).
5. Download this software by running ```git clone https://github.com/DesignSparkrs/RadioGlobe.git```
6. Run ```cd radioglobe```
7. (If you cloned to a folder other than ~/work, then run ```nano services/radioglobe.service``` and change the paths on
   lines 5 and 17 accordingly.  Repeat this in ```nano services/streaming.service```)
5. Run ```sudo ./install.sh```  This will install all dependencies and install the service so that the radio automatically
   starts when the Raspberry Pi is powered on in the future.
