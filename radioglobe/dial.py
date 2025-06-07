#! /usr/bin/python3
import time
import threading
import RPi.GPIO as GPIO


class Dial(threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

        # BCM pin numbering!
        GPIO.setmode(GPIO.BCM)
        GPIO.setup([17, 18], direction=GPIO.IN, pull_up_down=GPIO.PUD_UP)
        self.direction = 0

    def __del__(self):
        GPIO.cleanup()

    def get_direction(self):
        # Pickup the direction and zero it, so we only get it once
        return_val = self.direction
        self.direction = 0
        return return_val

    def run(self):
        while True:
            # We only need to check for an interrupt on one pin
            # because we can simply test the value of the other to
            # work out which direction the dial was turned.
            # We cannot modify the global direction variable because
            # it is processed afterwards, so it would not be thread safe
            GPIO.wait_for_edge(17, GPIO.FALLING)
            new_direction = GPIO.input(18)
            if not new_direction:
                new_direction = -1

            # Save the new_direction
            self.direction = new_direction

            # Debounce period
            time.sleep(0.3)
