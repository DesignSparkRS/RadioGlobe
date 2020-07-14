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

mixer_name = None

def set_volume(percent:int) -> int:
    global mixer_name

    if not mixer_name:
        get_control = subprocess.run(['amixer', 'scontrols'], stdout=subprocess.PIPE)
        control_match = re.match(r"Simple mixer control \'(.*)\'", str(get_control.stdout, encoding="utf-8").rstrip())
        if control_match:
            mixer_name = control_match.group(1)

    if percent > 100:
        percent = 100
    elif percent < 0:
        percent = 0
    subprocess.run(['amixer', 'set', mixer_name, ('{}%').format(percent)])

    # Return the percent volume, so that the caller doesn't have to handle capping to 0-100
    return percent

def check_url(url) -> str:
    """Returns only good urls, or None"""
    try:
        response = requests.get(url, timeout=0.1)
    except Timeout as e:
        print(f'URL Timeout, {url}, {e}')
    except Exception as e:
        print(f'URL error, {url}, {e}')
    else:
        if response.status_code == requests.codes.ok:
            return url
    return None


def launch(audio, url) -> 'pid':
    """Play url returning the vlc pid"""
    radio = subprocess.Popen(['cvlc', '--aout', audio, url])
    return radio.pid


class Streamer ():
    """A streaming audio player using vlc's command line"""

    def __init__(self, audio, url):
        self.audio = audio
        self.url = url
        self.radio_pid = None

    def play(self):
        with concurrent.futures.ProcessPoolExecutor() as executor:
            try:
                # Play streamer in a separate process
                ex = executor.submit(launch, self.audio, self.url)
            except Exception as e:
                print('URL Error', e)
            else:
                # Get the vlc process pid so it can be stopped (killed!)
                self.radio_pid = ex.result()
                print(self.radio_pid)

    def stop(self):
        """Kill the vlc process. It's a bit brutal but it works
        even for streams that send vlc into a race condition,
        which is probably a bug in vlc"""
        try:
            os.kill(self.radio_pid, signal.SIGKILL)
        except Exception as e:
            print('Error: ', e)
        else:
            print('Stopped: ', self.radio_pid)


if __name__ == "__main__":

    stations_file = 'stations.json'
    audio = 'alsa'  # or pulse
    clip_duration = 10

    with Path(stations_file).open(mode='r') as f:
        stations = json.load(f)

    # Get list of urls
    url_list = [url['url'].strip() for k, v in stations.items() for url in v['urls']]
    urls = list(set(url_list))  # De-duped list

    print(f'{len(urls)} URLs')

    while True:
        for url in urls:
            i = urls.index(url)
            if not check_url(url):
                print(f'Bad URL, {i}, {url}')
            else:
                print(f'Playing URL, {i}, {url}')
                streamer = Streamer(audio, url)
                streamer.play()
                time.sleep(clip_duration)
                streamer.stop()
