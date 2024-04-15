# Thanks to Peter Milne!
import time
import logging
import vlc


class Streamer():
    """
    A streaming audio player using python-vlc
    This improves handling of media list (pls and m3u's) streams
    """
    def __init__(self, audio='alsa', url=None):
        logging.debug(f"Starting Streamer: {audio}, {url}")
        self.audio = audio
        self.url = url
        self.instance = vlc.Instance()
        self.media = None
        self.mediaplayer = None
        self.is_playing = False

    def play(self, url):
        playlists = set(['pls', 'm3u'])
        url = url.strip()
        logging.debug(f"Playing URL {url}")

        if self.is_playing:
            self.stop()
        self.is_playing = True

        # We need a different type of media instance for urls containing playlists
        extension = (url.rpartition(".")[2])[:3]
        logging.debug(f"Extension: {extension}")
        if extension in playlists:
            logging.debug(f"Creating media_list_player...")
            self.mediaplayer = self.instance.media_list_player_new()
            self.media = self.instance.media_list_new([url])
            self.mediaplayer.set_media_list(self.media)
        else:
            logging.debug(f"Creating media_player...")
            self.mediaplayer = self.instance.media_player_new()
            self.media = self.instance.media_new(url)
            self.mediaplayer.set_media(self.media)

        self.mediaplayer.play()

    def stop(self):
        self.is_playing = False
        self.mediaplayer.stop()


if __name__ == "__main__":
    """python python_vlc_streaming.py ../json/london-stations.json"""
    import sys
    import files

    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.getLogger().setLevel(logging.DEBUG)

    clip_duration = 10

    stations_file = sys.argv[1]
    stations = files.load_stations(stations_file)

    # Get list of stations
    stations_list = []
    for k, v in stations.items():
        for v in v['urls']:
            stations_list.append(v)

    logging.debug(stations_list)
    logging.info(f"Station list length: {len(stations_list)} URLs")

    player = Streamer()
    for i, station in enumerate(stations_list):
        url = station['url']
        logging.info(f"Playing URL {i}, {station['name']}, {url}")
        player.play(url)
        time.sleep(clip_duration)

    logging.info("End of list")
