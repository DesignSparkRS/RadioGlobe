import time
import threading
import RPi.GPIO as GPIO

RED_PIN = 22
GREEN_PIN = 23
BLUE_PIN = 24

COLOURS = {
  "OFF":      None,
  "RED":      [RED_PIN],
  "GREEN":    [GREEN_PIN],
  "BLUE":     [BLUE_PIN],
  "CYAN":     [GREEN_PIN,  BLUE_PIN],
  "MAGENTA":  [RED_PIN,   BLUE_PIN],
  "YELLOW":   [RED_PIN,   GREEN_PIN],
  "WHITE":    [RED_PIN,   GREEN_PIN,  BLUE_PIN]
}


class RGB_LED (threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

        # BCM pin numbering!
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([RED_PIN, GREEN_PIN, BLUE_PIN], direction=GPIO.OUT, initial=GPIO.HIGH)

        self.state = 1
        self.colour_0 = "OFF"
        self.colour_1 = "OFF"
        self.colour_0_mem = None
        self.colour_1_mem = None

        self.timer = None

    def __del__(self):
        GPIO.cleanup()

    def set_static(self, colour=None: str, timeout_sec=None: float, restore_previous_on_timeout=False: bool):
        if timeout_sec:
            if self.timer:
                return

            self.timer = timeout_sec + 0.5
            if restore_previous_on_timeout:
                self.colour_0_mem = self.colour_0
                self.colour_1_mem = self.colour_1
            else:
                self.colour_0_mem = None
                self.colour_1_mem = None

        self.colour_0 = colour
        self.colour_1 = colour

        pins = COLOURS[colour]

        # All pins off (perhaps momentarily)
        GPIO.output([RED_PIN, GREEN_PIN, BLUE_PIN], GPIO.LOW)

        # Write required pins high
        if pins is not None:
            GPIO.output(pins, GPIO.HIGH)

    def set_blink(self, colour_0=None: str, colour_1="OFF": str, timeout_sec=None: float,
                  restore_previous_on_timeout=False: bool):
        if timeout_sec:
            if self.timer:
                return

            self.timer = timeout_sec + 0.5
            if restore_previous_on_timeout:
                self.colour_0_mem = self.colour_0
                self.colour_1_mem = self.colour_1
            else:
                self.colour_0_mem = None
                self.colour_1_mem = None

        self.colour_0 = colour_0
        self.colour_1 = colour_1

    def run(self):
        while True:
            if self.state == 0:
                self.state = 1
                pins = COLOURS[self.colour_1]
            else:
                self.state = 0
                pins = COLOURS[self.colour_0]

            # All pins off (perhaps momentarily)
            GPIO.output([RED_PIN, GREEN_PIN, BLUE_PIN], GPIO.LOW)

            # Write required pins high
            if pins is not None:
                GPIO.output(pins, GPIO.HIGH)

            # Flash/wait period
            time.sleep(0.5)

            # Turn off the light when the timer expires
            if self.timer:
                self.timer -= 0.5

                if self.timer <= 0:
                    self.timer = None
                    if self.colour_0_mem:
                        self.colour_0 = self.colour_0_mem
                        self.colour_0_mem = None
                    else:
                        self.colour_0 = "OFF"

                    if self.colour_1_mem:
                        self.colour_1 = self.colour_1_mem
                        self.colour_1_mem = None
                    else:
                        self.colour_1 = "OFF"


if __name__ == "__main__":
    led = RGB_LED(1, "LED")
    led.start()

    try:
        while True:
            led.set_blink("YELLOW", "BLUE")
            time.sleep(5)

            for colour in COLOURS:
                led.set_static(colour)
                time.sleep(0.5)
    except Exception:
        GPIO.cleanup()
        exit()
