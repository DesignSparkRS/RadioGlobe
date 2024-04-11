# Thanks to Peter Milne!
import time
import logging
import vlc


class Streamer ():
    """
    A streaming audio player using python-vlc
    This improves handling of media list (pls and m3u's) streams
    """

    def __init__(self, audio, url):
        logging.debug(f"Starting Streamer: {audio}, {url}")
        self.audio = audio
        self.url = url
        self.player = None

        playlists = set(['pls', 'm3u'])
        Instance = vlc.Instance()

        url = self.url.strip()
        logging.debug(f"Playing URL {url}")

        # We need a different type of media instance for urls containing playlists
        extension = (url.rpartition(".")[2])[:3]
        logging.debug(f"Extension: {extension}")
        if extension in playlists:
            logging.debug(f"Creating media_list_player...")
            player = Instance.media_list_player_new()
            media = Instance.media_list_new([url])
            player.set_media_list(media)
        else:
            logging.debug(f"Creating media_player...")
            player = Instance.media_player_new()
            media = Instance.media_new(url)
            player.set_media(media)

        self.player = player

    def play(self):
        self.player.play()

    def stop(self):
        self.player.stop()


if __name__ == "__main__":
    """python python-vlc-streaming.py ../stations.json"""
    import sys
    import files
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    # logging.getLogger().setLevel(logging.DEBUG)

    clip_duration = 10
    audio = 'alsa'

    stations_file = sys.argv[1]
    stations = files.load_stations(stations_file)

    # Get list of stations
    station_list = []
    for k, v in stations.items():
        for v in v['urls']:
            station_list.append(v)

    logging.debug(station_list)
    logging.info(f"Station list length: {len(station_list)} URLs")

    for i, station in enumerate(station_list):
        logging.info(f"Playing URL {i}, {station['name']}, {station['url']}")
        player = Streamer(audio, station['url'])
        player.play()
        time.sleep(clip_duration)
        player.stop()

    logging.info("End of list")
