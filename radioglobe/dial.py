import time
import threading
import RPi.GPIO as GPIO
import logging

MODE_STATION = "station_select"
MODE_CITY = "city_select"


class Dial(threading.Thread):
    def __init__(self, threadID, name, button_pin=27):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup([17, 18, button_pin], GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(
                button_pin, GPIO.BOTH, callback=self._button_callback, bouncetime=50
            )
            logging.info("Dial GPIO initialized (pins 17, 18, 27)")
        except Exception as e:
            logging.error(f"GPIO setup failed: {e}")
            raise
        self.direction = 0
        self.mode = MODE_STATION
        self.button_pin = button_pin
        self.button_press_time = None
        self.lock = threading.Lock()

    def __del__(self):
        GPIO.cleanup()
        logging.info("Dial GPIO cleaned up")

    def get_direction(self):
        with self.lock:
            return_val = self.direction
            self.direction = 0
            return return_val

    def get_mode(self):
        with self.lock:
            return self.mode

    def _button_callback(self, channel):
        with self.lock:
            try:
                if GPIO.input(self.button_pin) == GPIO.LOW:  # Pressed
                    self.button_press_time = time.time()
                    logging.debug("Jog button pressed")
                else:  # Released
                    if self.button_press_time is not None:
                        press_duration = time.time() - self.button_press_time
                        # Toggle mode instantly on release, no hold required
                        self.mode = (
                            MODE_CITY if self.mode == MODE_STATION else MODE_STATION
                        )
                        logging.info(f"Mode toggled to {self.mode}")
                        self.button_press_time = None
                        logging.debug(
                            f"Jog button released, duration: {press_duration:.2f}s"
                        )
            except Exception as e:
                logging.error(f"Button callback failed: {e}")

    def run(self):
        try:
            while True:
                GPIO.wait_for_edge(17, GPIO.FALLING)
                new_direction = GPIO.input(18)
                if new_direction:
                    new_direction = -1
                else:
                    new_direction = 1
                with self.lock:
                    self.direction = new_direction
                logging.debug(f"Dial direction: {new_direction}")
                time.sleep(0.3)
        except Exception as e:
            logging.error(f"Dial thread failed: {e}")
