import time
import threading
import liquidcrystal_i2c

DISPLAY_I2C_ADDRESS = 0x27
DISPLAY_I2C_PORT = 1
DISPLAY_COLUMNS = 20
DISPLAY_ROWS = 4


class Display (threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.lcd = liquidcrystal_i2c.LiquidCrystal_I2C(DISPLAY_I2C_ADDRESS, DISPLAY_I2C_PORT, numlines=DISPLAY_ROWS)
        self.buffer = ["" for row in range(0, DISPLAY_ROWS)]
        self.changed = False

    def run(self):
        while True:
            if self.changed:
                for line_num in range(0, DISPLAY_ROWS):
                    self.lcd.printline(line_num, self.buffer[line_num])
                self.changed = False
            time.sleep(0.1)

    def clear(self):
        self.buffer[0] = ""
        self.buffer[1] = ""
        self.buffer[2] = ""
        self.buffer[3] = ""
        self.changed = True

    def message(self, line_1="": str, line_2="": str, line_3="": str, line_4="": str):
        self.buffer[0] = line_1.center(DISPLAY_COLUMNS)
        self.buffer[1] = line_2.center(DISPLAY_COLUMNS)
        self.buffer[2] = line_3.center(DISPLAY_COLUMNS)
        self.buffer[3] = line_4.center(DISPLAY_COLUMNS)
        self.changed = True

    def update(self, north: int, east: int, location: str, volume: int, station: str, arrows: bool):
        if north >= 0:
            self.buffer[0] = ("{:5.2f}N, ").format(north)
        else:
            self.buffer[0] = ("{:5.2f}S, ").format(abs(north))

        if east >= 0:
            self.buffer[0] += ("{:6.2f}E").format(east)
        else:
            self.buffer[0] += ("{:6.2f}W").format(abs(east))

        self.buffer[0] = self.buffer[0].center(DISPLAY_COLUMNS)
        self.buffer[1] = location.center(DISPLAY_COLUMNS)

        # Volume display
        self.buffer[2] = ""
        bar_length = (volume * DISPLAY_COLUMNS) // 100
        for i in range(bar_length):
            self.buffer[2] += "-"
        for i in range(bar_length, DISPLAY_COLUMNS):
            self.buffer[2] += " "

        if arrows:
            # Trim/pad the station name to fit arrows at each side of the display
            station = station[:(DISPLAY_COLUMNS - 4)]
            padding = DISPLAY_COLUMNS - 4 - len(station)
            start_padding = padding // 2
            end_padding = padding - start_padding
            while start_padding:
                station = " " + station
                start_padding -= 1
            while end_padding:
                station += " "
                end_padding -= 1

            station = "< " + station + " >"
        self.buffer[3] = station.center(DISPLAY_COLUMNS)

        self.changed = True


if __name__ == "__main__":
    try:
        display_thread = Display(1, "Display")
        display_thread.start()
        display_thread.update(51.45, -2.59, "Bristol, United Kingdom", 45, "BBC Radio Bristol", True)
        time.sleep(5)
        display_thread.update(0, 0, "Clearing in 2s...", 0, "", False)
        time.sleep(2)
        display_thread.clear()

    except Exception:
        exit()
