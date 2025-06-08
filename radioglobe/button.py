#! /usr/bin/python3
import time
import threading
import RPi.GPIO as GPIO


class Button(threading.Thread):
    def __init__(self, threadID, name, gpio_pin):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name
        self.pin = gpio_pin
        self.held_time = -1
        self.latched_time = -1
        self.last_event_time = 0  # Track last valid event (press or release)
        self.debounce_time = 0.2  # 200ms debounce period (adjustable)

        # BCM pin numbering!
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        # Detect both press (FALLING) and release (RISING) with 200ms debounce
        GPIO.add_event_detect(
            self.pin, GPIO.BOTH, callback=self.handle_event, bouncetime=200
        )

    def __del__(self):
        GPIO.cleanup()

    def handle_event(self, channel):
        current_time = time.time()
        if current_time - self.last_event_time < self.debounce_time:
            return  # Ignore if within debounce window

        # Wait briefly to let bounce settle, then read pin state
        time.sleep(0.01)  # 10ms delay to stabilize reading
        pin_state = GPIO.input(self.pin)

        if pin_state == GPIO.LOW:  # Button pressed
            self.held_time = 0
            self.latched_time = -1  # Reset latched time until release
        elif pin_state == GPIO.HIGH and self.held_time >= 0:  # Button released
            self.latched_time = self.held_time  # Record duration of press
            self.held_time = -1  # Reset for next press

        self.last_event_time = current_time

    def get_time_held(self):
        return_val = self.latched_time
        if self.held_time == -1:  # Clear latch only when button is released
            self.latched_time = -1
        return return_val

    def clear(self):
        self.held_time = -1
        self.latched_time = -1

    def run(self):
        while True:
            if self.held_time >= 0:  # Button is being held
                self.held_time += 0.01  # Increment by 10ms
            time.sleep(0.01)  # Check every 10ms for smoother timing


class Button_Manager:
    def __init__(self, name_and_pin_tuples: list):
        self.buttons = []
        for index, (name, pin) in enumerate(name_and_pin_tuples):
            self.buttons.append(Button(index, name, pin))

        for button in self.buttons:
            button.start()

    def update(self, receiving_queue: list):
        for button in self.buttons:
            time_held = button.get_time_held()

            if time_held != -1:
                receiving_queue.append([button.name, time_held])

    def clear(self, button_name: str):
        for button in self.buttons:
            if button.name == button_name:
                button.clear()
                break


if __name__ == "__main__":
    button_manager = Button_Manager(
        [
            ("Jog_push", 27),
            ("Top", 5),  # Could be volume up
            ("Mid", 6),  # Could be volume down
            ("Low", 12),
            ("Shutdown", 26),
        ]
    )
    button_events = []

    while True:
        button_manager.update(button_events)

        while len(button_events) > 0:
            event = button_events.pop()
            print(f"Button {event[0]} pressed for {event[1]:.2f} seconds")
        time.sleep(0.1)
