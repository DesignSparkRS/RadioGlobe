# Thanks to Peter Milne!
import subprocess
import logging


class Streamer:
    """A streaming audio player using VLC's command line"""

    def __init__(self, audio, url):
        logging.info("Starting Streamer: %s, %s", audio, url)
        self.audio = audio
        self.url = url
        self.process = None

    def play(self):
        try:
            logging.info("Launching VLC for URL: %s", self.url)
            self.process = subprocess.Popen(
                ["cvlc", "--intf", "dummy", "--aout", self.audio, self.url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logging.info("Streamer started with PID %s", self.process.pid)
        except Exception as e:
            logging.info("Error launching Streamer: %s", e)
            self.process = None

    def stop(self):
        """Stop the VLC process."""
        if self.process is None:
            logging.info("No Streamer process to stop")
            return

        if self.process.poll() is not None:
            logging.info(
                "Streamer process already exited with code %s", self.process.returncode
            )
            self.process = None
            return

        try:
            logging.info("Terminating Streamer PID %s", self.process.pid)
            self.process.terminate()  # send SIGTERM first
            try:
                self.process.wait(timeout=5)
                logging.info("Streamer PID %s terminated cleanly", self.process.pid)
            except subprocess.TimeoutExpired:
                logging.info(
                    "Streamer PID %s did not terminate, killing", self.process.pid
                )
                self.process.kill()  # send SIGKILL if needed
                self.process.wait()
                logging.info("Streamer PID %s killed", self.process.pid)
        except Exception as e:
            logging.info("Error stopping Streamer: %s", e)
        finally:
            self.process = None
