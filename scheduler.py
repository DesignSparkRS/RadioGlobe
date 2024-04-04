import time
import threading

EXPIRY = 0
RELOAD = 1
CALLBACK = 2


class Scheduler (threading.Thread):
    def __init__(self, threadID, name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.name = name

        self.time = 0
        self.timers = []

    def attach_timer(self, callback: callable, initial_value_sec: int, one_shot=True):
        # Overwrite existing timer for the same callback
        for exist_timer in self.timers:
            if exist_timer[CALLBACK] == callback:
                exist_timer[EXPIRY] = self.time + initial_value_sec
                if not one_shot:
                    new_timer[RELOAD] = initial_value_sec
                return

        # Else make a new timer
        new_timer = [None, None, None]
        new_timer[EXPIRY] = self.time + initial_value_sec
        new_timer[CALLBACK] = callback
        if not one_shot:
            new_timer[RELOAD] = initial_value_sec
        self.timers.append(new_timer)

    def run(self):
        while True:
            time.sleep(1)
            self.time += 1

            # Loop all the timers to see if they've expired.  Call their callback if they have, then delete if they're
            # one shot timers
            num_timers = len(self.timers)
            timer = 0
            while timer < num_timers:
                if self.time >= self.timers[timer][EXPIRY]:
                    self.timers[timer][CALLBACK]()
                    if self.timers[timer][RELOAD]:
                        self.timers[timer][EXPIRY] = self.time + self.timers[timer][RELOAD]
                    else:
                        self.timers.__delitem__(timer)
                        num_timers -= 1
                timer += 1


if __name__ == "__main__":
    def print_one_shot():
        print("One shot")

    def print_reload():
        print("Reload")

    scheduler = Scheduler(1, "SCHEDULER")
    scheduler.start()

    # The first one shouldn't expire, because the second overwrites it!
    scheduler.attach_timer(print_one_shot, 5)
    scheduler.attach_timer(print_one_shot, 8)
    scheduler.attach_timer(print_reload, 6, one_shot=False)

    try:
        while True:
            time.sleep(0.5)
    except Exception:
        exit()
