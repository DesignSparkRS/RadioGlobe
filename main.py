import re
import time
import threading
import subprocess
import logging

# from python-vlc-streaming import Streamer, set_volume
from streaming.python_vlc_streaming import Streamer
import database
import radio_config
from display import Display
from positional_encoders import *
from ui_manager import UI_Manager
from rgb_led import RGB_LED
from scheduler import Scheduler

format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logging.getLogger().setLevel(logging.DEBUG)

VOLUME_INCREMENT = 5

state = "start"
volume_display = False
volume = 95
jog = 0
last_jog = 0
state_entry = True

ui_manager = UI_Manager()
streamer = Streamer(audio=radio_config.AUDIO_SERVICE)

stations_data = database.Load_Stations(radio_config.STATIONS_JSON)


# This is used to increase the size of the area searched around the coords
# For example, fuzziness 2, latitude 50 and longitude 0 will result in a
# search square 48,1022 to 52,2 (with encoder resolution 1024)
def Look_Around(latitude: int, longitude: int, fuzziness: int):
    # Offset fuzziness, so 0 means only the given coords
    fuzziness += radio_config.FUZZINESS

    search_coords = []

    # Work out how big the perimeter is for each layer out from the origin
    ODD_NUMBERS = [((i * 2) + 1) for i in range(0, fuzziness)]

    # With each 'layer' of fuzziness we need a starting point.  70% of people are right-eye dominant and
    # the globe is likely to be below the user, so go down and left first then scan horizontally, moving up
    for layer in range(0, fuzziness):
        for y in range(0, ODD_NUMBERS[layer]):
            for x in range(0, ODD_NUMBERS[layer]):
                coord_x = (latitude + x - (ODD_NUMBERS[layer] // 2)) % ENCODER_RESOLUTION
                coord_y = (longitude + y - (ODD_NUMBERS[layer] // 2)) % ENCODER_RESOLUTION
                if [coord_x, coord_y] not in search_coords:
                    search_coords.append([coord_x, coord_y])

    return search_coords


def Back_To_Tuning():
    global state
    global state_entry

    if state != "tuning":
        state = "tuning"
        state_entry = True


def Clear_Volume_Display():
    global volume_display

    volume_display = False


def Process_UI_Events():
    global state
    global state_entry
    global volume
    global volume_display
    global jog
    global ui_manager
    global encoders_thread
    global rgb_led

    ui_events = []
    ui_manager.update(ui_events)

    for event in ui_events:
        if event[0] == "Jog":
            if event[1] == 1:
                # Next station
                jog += 1
            elif event[1] == -1:
                # Previous station
                jog -= 1
            print(jog)

        elif event[0] == "Volume":
            if event[1] == 1:
                volume += VOLUME_INCREMENT
                # volume = set_volume(volume)
                volume_display = True
                scheduler.attach_timer(Clear_Volume_Display, 3)
                rgb_led.set_static("BLUE", timeout_sec=0.5, restore_previous_on_timeout=True)
                print(("Volume up: {}%").format(volume))
            elif event[1] == -1:
                if state == "shutdown_confirm":
                    Back_To_Tuning()
                else:
                    volume -= VOLUME_INCREMENT
                    # volume = set_volume(volume)
                    volume_display = True
                    scheduler.attach_timer(Clear_Volume_Display, 3)
                    rgb_led.set_static("BLUE", timeout_sec=0.5, restore_previous_on_timeout=True)
                    print(("Volume down: {}%").format(volume))

        elif event[0] == "Random":
            print("Toggle jog mode - not implemented")

        elif event[0] == "Shutdown":
            state = "shutdown_confirm"
            state_entry = True

        elif event[0] == "Calibrate":
            # Zero the positional encoders
            offsets = encoders_thread.zero()
            database.Save_Calibration(offsets[0], offsets[1])
            rgb_led.set_static("GREEN", timeout_sec=0.5, restore_previous_on_timeout=True)
            print("Calibrated")
            display_thread.message(
                line_1="",
                line_2="Calibrated!",
                line_3="",
                line_4="")

            time.sleep(1)

        elif event[0] == "Confirm":
            if state == "shutdown_confirm":
                state = "shutdown"
                state_entry = True
            else:
                pass


# PROGRAM START
database.Build_Map(radio_config.STATIONS_JSON, radio_config.STATIONS_MAP)
index_map = database.Load_Map(radio_config.STATIONS_MAP)
encoder_offsets = database.Load_Calibration()

# Positional encoders - used to select latitude and longitude
encoders_thread = Positional_Encoders(2, "Encoders", encoder_offsets[0], encoder_offsets[1])
encoders_thread.start()

display_thread = Display(3, "Display")
display_thread.start()

rgb_led = RGB_LED(20, "RGB_LED")
rgb_led.start()

scheduler = Scheduler(50, "SCHEDULER")
scheduler.start()

# set_volume(volume)

while True:
    if state == "start":
        # Entry - setup state
        if state_entry:
            state_entry = False
            display_thread.message(
                line_1="Radio Globe",
                line_2="Made for DesignSpark",
                line_3="Jude Pullen, Donald",
                line_4="Robson, Pete Milne")
            scheduler.attach_timer(Back_To_Tuning, 3)

    elif state == "tuning":
        # Entry - setup state
        if state_entry:
            state_entry = False
            rgb_led.set_blink("WHITE")
            display_thread.clear()

        # Normal operation
        else:
            coordinates = encoders_thread.get_readings()
            search_area = Look_Around(coordinates[0], coordinates[1], fuzziness=3)
            location_name = ""
            stations_list = []
            url_list = []

            # Check the search area.  Saving the first location name encountered
            # and all radio stations in the area, in order encountered
            for ref in search_area:
                index = index_map[ref[0]][ref[1]]

                if index != 0xFFFF:
                    encoders_thread.latch(coordinates[0], coordinates[1], stickiness=3)
                    state = "playing"
                    state_entry = True
                    location = database.Get_Location_By_Index(index)
                    if location_name == "":
                        location_name = location

                    # for station in database.stations_data[location]["urls"]:
                    for station in stations_data[location]["urls"]:
                        stations_list.append(station["name"])
                        url_list.append(station["url"])

            # Provide 'helper' coordinates
            latitude = round((360 * coordinates[0] / ENCODER_RESOLUTION - 180), 2)
            longitude = round((360 * coordinates[1] / ENCODER_RESOLUTION - 180), 2)

            if volume_display:
                volume_disp = volume
            else:
                volume_disp = 0

            display_thread.update(latitude, longitude,
                                  "Tuning...", volume_disp, "", False)

    elif state == "playing":
        # Entry - setup
        if state_entry:
            state_entry = False
            jog = 0
            last_jog = 0
            rgb_led.set_static("RED", timeout_sec=3.0)

            # Get display coordinates - from file, so there's no jumping about
            latitude = stations_data[location]["coords"]["n"]
            longitude = stations_data[location]["coords"]["e"]

            # Play the top station
            streamer.play(url_list[jog])

        # Exit back to tuning state if latch has 'come unstuck'
        elif not encoders_thread.is_latched():
            streamer.stop()
            state = "tuning"
            state_entry = True

        # If the jog dial is used, stop the stream and restart with the new url
        elif jog != last_jog:
            # Restrict the jog dial value to the bounds of stations_list
            jog %= len(stations_list)
            last_jog = jog

            streamer.play(url_list[jog])

        # Idle operation - just keep display updated
        else:
            if volume_display:
                volume_disp = volume
            else:
                volume_disp = 0

            # Add arrows to the display if there is more than one station here
            if len(stations_list) > 1:
                display_thread.update(latitude, longitude, location_name, volume_disp, stations_list[jog], True)
            elif len(stations_list) == 1:
                display_thread.update(latitude, longitude, location_name, volume_disp, stations_list[jog], False)

    elif state == "shutdown_confirm":
        if state_entry:
            state_entry = False
            display_thread.clear()
            time.sleep(0.1)
            display_thread.message(
                line_1="Really shut down?",
                line_2="<- Press mid button ",
                line_3="to confirm or",
                line_4="<- bottom to cancel.")

            # Auto-cancel in 5s
            scheduler.attach_timer(Back_To_Tuning, 5)

    elif state == "shutdown":
        if state_entry:
            state_entry = False
            display_thread.clear()
            time.sleep(0.1)
            display_thread.message(
                line_1="Shutting down...",
                line_2="Please wait 10 sec",
                line_3="before disconnecting",
                line_4="power.")
            subprocess.run(["sudo", "poweroff"])

    else:
        # Just in case!
        state = "tuning"

    Process_UI_Events()

    # Avoid unnecessarily high polling
    time.sleep(0.1)

# Clean up threads
encoders_thread.join()
