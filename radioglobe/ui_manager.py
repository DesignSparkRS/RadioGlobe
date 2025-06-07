#! /usr/bin/python3
import time
from button import Button_Manager
from dial import Dial

SHUTDOWN_HOLD_TIME = 3
CALIBRATE_HOLD_TIME = 5


class UI_Manager:
    def __init__(self):
        self.button_manager = Button_Manager(
            [("Jog_push", 27), ("Top", 5), ("Mid", 6), ("Low", 12), ("Shutdown", 26)]
        )

        self.dial = Dial(10, "Jog")
        self.dial.start()

    def __del__(self):
        del self.button_manager
        del self.dial

    def update(self, receiving_queue: list):
        # Get control events
        dial_direction = self.dial.get_direction()

        ui_events = []
        if dial_direction != 0:
            ui_events.append(["Jog", dial_direction])

        button_events = []
        self.button_manager.update(button_events)

        # Convert button events into ui_events
        for event in button_events:
            if event[0] == "Shutdown" and event[1] > SHUTDOWN_HOLD_TIME:
                # Just overwrite the queue as there's no point in doing anything else
                ui_events = [["Shutdown", 0]]
                self.button_manager.clear("Shutdown")
                break
            elif event[0] == "Jog_push":
                if event[1] > SHUTDOWN_HOLD_TIME:
                    # Just overwrite the queue as there's no point in doing anything else
                    ui_events = [["Shutdown", 0]]
                    self.button_manager.clear("Jog_push")
                    break
                else:
                    ui_events.append(["Random", 0])
            elif event[0] == "Mid":
                if event[1] > CALIBRATE_HOLD_TIME:
                    ui_events.append(["Calibrate", 0])
                    self.button_manager.clear("Mid")
                else:
                    ui_events.append(["Confirm", 0])
            elif event[0] == "Top":
                ui_events.append(["Volume", 1])
            elif event[0] == "Low":
                ui_events.append(["Volume", -1])

        # Put the button events into the supplied queue (a list)
        receiving_queue.extend(ui_events)


if __name__ == "__main__":
    ui_manager = UI_Manager()
    ui_events = []

    while True:
        ui_manager.update(ui_events)

        while len(ui_events) > 0:
            print(ui_events.pop())

        time.sleep(0.1)
