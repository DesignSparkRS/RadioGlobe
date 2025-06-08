#! /usr/bin/python3
import time
import threading
import liquidcrystal_i2c
import logging

DISPLAY_I2C_ADDRESS = 0x27
DISPLAY_I2C_PORT = 1
DISPLAY_COLUMNS = 20
DISPLAY_ROWS = 4


class Display(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.lcd = liquidcrystal_i2c.LiquidCrystal_I2C(
            DISPLAY_I2C_ADDRESS, DISPLAY_I2C_PORT, numlines=DISPLAY_ROWS
        )
        self.buffer = [""] * DISPLAY_ROWS
        self.changed = False
        self.running = True
        self.station = ""  # Full station name
        self.scroll_pos = 0  # Current scroll position
        self.scroll_active = False  # Scrolling state
        self.last_scroll_time = time.time()  # Track time for pauses

    def run(self):
        while self.running:
            current_time = time.time()
            if self.changed:
                for line_num in range(DISPLAY_ROWS):
                    self.lcd.printline(line_num, self.buffer[line_num])
                self.changed = False
                # logging.debug(f"Display updated: {self.buffer}")
            if self.scroll_active and len(self.station) > DISPLAY_COLUMNS:
                self._scroll_station(current_time)
            time.sleep(0.05)  # 50ms for smooth updates

    def stop(self):
        self.running = False

    def clear(self):
        self.buffer = [""] * DISPLAY_ROWS
        self.changed = True
        self.scroll_active = False
        logging.debug("Display cleared")

    def message(
        self, line_1: str = "", line_2: str = "", line_3: str = "", line_4: str = ""
    ):
        self.buffer[0] = line_1.center(DISPLAY_COLUMNS)
        self.buffer[1] = line_2.center(DISPLAY_COLUMNS)
        self.buffer[2] = line_3.center(DISPLAY_COLUMNS)
        self.buffer[3] = line_4.center(DISPLAY_COLUMNS)
        self.changed = True
        self.scroll_active = False
        logging.debug(f"Message set: {self.buffer}")

    def update(
        self,
        north: int,
        east: int,
        location: str,
        volume: int,
        station: str,
        arrows: bool,
    ):
        # Coordinates
        if north >= 0:
            self.buffer[0] = f"{north:5.2f}N, "
        else:
            self.buffer[0] = f"{abs(north):5.2f}S, "
        if east >= 0:
            self.buffer[0] += f"{east:6.2f}E"
        else:
            self.buffer[0] += f"{abs(east):6.2f}W"
        self.buffer[0] = self.buffer[0].center(DISPLAY_COLUMNS)

        # Location
        self.buffer[1] = location.center(DISPLAY_COLUMNS)

        # Volume bar
        bar_length = (volume * DISPLAY_COLUMNS) // 100 if volume > 0 else 0
        self.buffer[2] = "-" * bar_length + " " * (DISPLAY_COLUMNS - bar_length)

        # Station Name Handling
        if station != self.station:  # Only reset if station changes
            self.station = station
            self.scroll_pos = 0
            self.last_scroll_time = time.time()
            logging.debug(f"Station set to: {station}")
        if len(station) <= DISPLAY_COLUMNS:
            self.buffer[3] = station.center(DISPLAY_COLUMNS)
            self.scroll_active = False
        else:
            self.scroll_active = True
        self.changed = True

    def _scroll_station(self, current_time):
        if not self.scroll_active:
            return

        scroll_speed = 0.2  # 200ms per character shift
        pause_duration = 2  # 2s pause at start only
        separator = " - "
        padded_station = self.station + separator
        display_text = padded_station + padded_station  # Duplicate for looping
        max_pos = len(padded_station)

        elapsed = current_time - self.last_scroll_time

        if self.scroll_pos == 0 and elapsed < pause_duration:
            self.buffer[3] = self.station[:DISPLAY_COLUMNS]
        elif self.scroll_pos == 0 and elapsed >= pause_duration:
            self.scroll_pos += 1
            self.last_scroll_time = current_time
            self.buffer[3] = display_text[
                self.scroll_pos : self.scroll_pos + DISPLAY_COLUMNS
            ]
            # logging.debug(
            #     f"Scrolling started: pos={self.scroll_pos}, text='{self.buffer[3]}'"
            # )
        else:  # Continuous scrolling, no end pause
            if elapsed >= scroll_speed:
                self.scroll_pos = (self.scroll_pos + 1) % max_pos  # Loop back to start
                self.buffer[3] = display_text[
                    self.scroll_pos : self.scroll_pos + DISPLAY_COLUMNS
                ]
                self.last_scroll_time = current_time
                # logging.debug(
                #     f"Scrolling: pos={self.scroll_pos}, text='{self.buffer[3]}'"
                # )

        self.changed = True


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    try:
        display_thread = Display(1, "Display")
        display_thread.start()

        # Test short name
        display_thread.update(
            51.45, -2.59, "Bristol, UK", 45, "BBC Radio Bristol", False
        )
        time.sleep(5)

        # Test long name
        display_thread.update(
            51.45, -2.59, "Bristol, UK", 45, "BBC Radio Bristol Extra Long Name", False
        )
        time.sleep(20)  # Watch it scroll

        display_thread.update(0, 0, "Clearing in 2s...", 0, "", False)
        time.sleep(2)
        display_thread.clear()
        display_thread.stop()
        display_thread.join()

    except KeyboardInterrupt:
        display_thread.stop()
        display_thread.join()
