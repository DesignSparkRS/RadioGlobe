import time
from button import Button_Manager
from dial import Dial
import logging

SHUTDOWN_HOLD_TIME = 3
CALIBRATE_HOLD_TIME = 5


class UI_Manager:
    def __init__(self):
        try:
            # self.button_manager = Button_Manager([("Top", 5), ("Mid", 6), ("Low", 12), ("Shutdown", 26)])
            self.button_manager = Button_Manager(
                [("Top", 5), ("Mid", 6), ("Low", 12), ("Shutdown", 27)]
            )
            self.dial = Dial(10, "Jog", button_pin=27)
            self.dial.start()
            self.last_mode = self.dial.get_mode()
            logging.info("UI_Manager initialized")
        except Exception as e:
            logging.error(f"UI_Manager init failed: {e}")
            raise

    def __del__(self):
        del self.button_manager
        del self.dial
        logging.info("UI_Manager cleaned up")

    def update(self, receiving_queue: list):
        try:
            dial_direction = self.dial.get_direction()

            current_mode = self.dial.get_mode()
            ui_events = []
            if dial_direction != 0:
                ui_events.append(["Jog", dial_direction])
            if current_mode != self.last_mode:
                ui_events.append(["Mode_Toggle", 0])
                self.last_mode = current_mode

            button_events = []
            self.button_manager.update(button_events)
            for event in button_events:
                if event[0] == "Shutdown" and event[1] > SHUTDOWN_HOLD_TIME:
                    # ui_events = [["Shutdown", 0]]
                    ui_events.append(["Shutdown", 0])
                    self.button_manager.clear("Shutdown")
                    logging.debug("Shutdown event triggered")
                    break
                elif event[0] == "Mid":
                    if event[1] > CALIBRATE_HOLD_TIME:
                        ui_events.append(["Calibrate", 0])
                        self.button_manager.clear("Mid")
                        logging.debug("Calibrate event triggered")
                    else:
                        ui_events.append(["Confirm", 0])
                        logging.debug("Confirm event triggered")
                elif event[0] == "Top":
                    ui_events.append(["Volume", 1])
                    logging.debug("Volume up event")
                elif event[0] == "Low":
                    ui_events.append(["Volume", -1])
                    logging.debug("Volume down event")
            receiving_queue.extend(ui_events)
        except Exception as e:
            logging.error(f"UI update failed: {e}")


if __name__ == "__main__":
    ui_manager = UI_Manager()
    ui_events = []

    while True:
        ui_manager.update(ui_events)

        while len(ui_events) > 0:
            print(ui_events.pop())

        time.sleep(0.1)
