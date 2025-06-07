#! /usr/bin/python3
import time
import threading
import RPi.GPIO as GPIO

class Button (threading.Thread):
  def __init__(self, threadID, name, gpio_pin):
    threading.Thread.__init__(self)
    self.threadID = threadID
    self.name = name
    self.pin = gpio_pin
    self.held_time = -1
    self.latched_time = -1

    # BCM pin numbering!
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(self.pin, direction=GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(self.pin, GPIO.FALLING, callback=self.start_timer, bouncetime=150)

  def __del__(self):
    GPIO.cleanup()

  def start_timer(self, arg):
    time.sleep(0.1)
    if GPIO.input(self.pin) == GPIO.LOW:
      self.held_time = 0
    else:
      # Momentary press
      self.latched_time = 0

  def get_time_held(self):
    return_val = self.latched_time

    # Only clear the latch if the button has been released
    if self.held_time == -1:
      self.latched_time = -1
    return return_val

  def clear(self):
    self.held_time = -1
    self.latched_time = -1

  def run(self):
    while True:
      if self.held_time >= 0:
        if GPIO.input(self.pin) == GPIO.HIGH:
          self.latched_time = self.held_time
          self.held_time = -1
        else:
          self.held_time += 1
          self.latched_time += 1

      time.sleep(1)

class Button_Manager:
  def __init__(self, name_and_pin_tuples:list):
    self.buttons = []

    for (name, pin) in name_and_pin_tuples:
      index = len(self.buttons)
      self.buttons.append(Button(index, name, pin))

    for button in self.buttons:
      button.start()

  def update(self, receiving_queue:list):
    for button in self.buttons:
      time_held = button.get_time_held()

      if time_held != -1:
        receiving_queue.append([button.name, time_held])

  def clear(self, button_name:str):
    for button in self.buttons:
      if button.name == button_name:
        button.clear()
        break

if __name__ == "__main__":
  button_manager = Button_Manager([("Jog_push", 27), ("Top", 5), ("Mid", 6), ("Low", 12), ("Shutdown", 26)])
  button_events = []

  while True:
    button_manager.update(button_events)

    while len(button_events) > 0:
      print(button_events.pop())

    time.sleep(0.1)
