#! /usr/bin/python3
# Thanks to Peter Milne!
import time
import subprocess
import os
import signal
from pathlib import Path
import json
import re
import requests
from requests.exceptions import Timeout
import concurrent.futures
import logging
import random

mixer_name = None


def set_volume(volume: int) -> int:
    logging.info("Setting volume: %u", volume)
    global mixer_name

    if not mixer_name:
        get_control = subprocess.run(['amixer', 'scontrols'], stdout=subprocess.PIPE)
        control_match = re.match(r"Simple mixer control \'(.*)\'", str(get_control.stdout, encoding="utf-8").rstrip())
        if control_match:
            mixer_name = control_match.group(1)
    # a value between 0 and 100
    if volume > 100:
        volume = 100
    elif volume < 0:
        volume = 0
    command = ["amixer", "sset", "Master", "{}%".format(volume)]
    subprocess.Popen(command)
    # Return the volume, so that the caller doesn't have to handle capping to 0-100
    return volume


def check_url(url: str) -> str | None:
    """Returns only good urls, or None"""
    try:
        response = requests.get(url, timeout=0.1)
    except Timeout as e:
        logging.debug("URL Timeout, %s, %s", url, e)
    except Exception as e:
        logging.debug("URL Error, %s, %s", url, e)
    else:
        if response.status_code == requests.codes.ok:
            return url
    return None


def launch(audio: str, url: str) -> int:
    """Play url returning the vlc pid"""
    logging.debug("Launching audio: %s, %s", audio, url)
    radio = subprocess.Popen(['cvlc', '--aout', audio, url])
    return radio.pid


class Streamer ():
    """A streaming audio player using vlc's command line"""

    def __init__(self, audio, url):
        logging.debug("Starting Streamer: %s, %s", audio, url)
        self.audio = audio
        self.url = url
        self.radio_pid = None

    def play(self):
        with concurrent.futures.ProcessPoolExecutor() as executor:
            try:
                # Play streamer in a separate process
                ex = executor.submit(launch, self.audio, self.url)
                logging.debug("Pool Executor: %s, %s", self.audio, self.url)
            except Exception as e:
                logging.debug("Pool Executor error: %s", e)
            else:
                # Get the vlc process pid so it can be stopped (killed!)
                self.radio_pid = ex.result()
                logging.debug("Pool Executor PID: %s", self.radio_pid)

    def stop(self):
        """Kill the vlc process. It's a bit brutal but it works
        even for streams that send vlc into a race condition,
        which is probably a bug in vlc"""
        try:
            os.kill(self.radio_pid, signal.SIGKILL)
            logging.debug("Killing Streamer PID: %s", self.radio_pid)
        except Exception as e:
            logging.debug("Kill Streamer error: %s", e)


if __name__ == "__main__":
    """
    python streaming.py 'london-stations.json'
    """
    import sys

    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    # logging.getLogger().setLevel(logging.DEBUG)

    stations_file = sys.argv[1]
    audio = 'alsa'  # or pulse
    clip_duration = 10

    with Path(stations_file).open(mode='r', encoding='utf8') as f:
        stations = json.load(f)

    set_volume(50)

    # Get list of urls
    url_list = [url['url'].strip() for k, v in stations.items() for url in v['urls']]
    urls = list(set(url_list))  # De-duped list
    top5 = urls[:5]
    logging.info("%s", top5)

    logging.info("Station list length: %s, URLs", len(urls))

    while True:
        i = random.choice(range(len(urls)))
        url = urls[i]
        logging.info("Playing URL, %s, %s", i, url)
        streamer = Streamer(audio, url)
        streamer.play()
        time.sleep(clip_duration)
        streamer.stop()
