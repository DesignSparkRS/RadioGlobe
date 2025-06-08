import time
import subprocess
import logging

from streaming import Streamer
import database
from display import Display
from positional_encoders import Positional_Encoders, ENCODER_RESOLUTION
from ui_manager import UI_Manager
from rgb_led import RGB_LED
from scheduler import Scheduler
from urllib.parse import urlsplit, urlunsplit
from dial import MODE_STATION, MODE_CITY

RADIOGLOBE_VERSION = "1.2.0"
AUDIO_SERVICE = "pulse"
VOLUME_INCREMENT = 5

state = "start"
volume_display = False
volume = 95
jog = 0
last_jog = -1
state_entry = True
current_mode = MODE_STATION
nearby_cities = []
coordinates = [0, 0]
last_activity_time = 0


ui_manager = None
encoders_thread = None
display_thread = None
rgb_led = None
scheduler = None
streamer = None


# This is used to increase the size of the area searched around the coords
# For example, fuzziness 2, latitude 50 and longitude 0 will result in a
# search square 48,1022 to 52,2 (with encoder resolution 1024)
def Look_Around(latitude: int, longitude: int, fuzziness: int):
    # Offset fuzziness, so 0 means only the given coords
    fuzziness += 1

    search_coords = []

    # Work out how big the perimeter is for each layer out from the origin
    ODD_NUMBERS = [((i * 2) + 1) for i in range(0, fuzziness)]

    # With each 'layer' of fuzziness we need a starting point.  70% of people are right-eye dominant and
    # the globe is likely to be below the user, so go down and left first then scan horizontally, moving up
    for layer in range(0, fuzziness):
        for y in range(0, ODD_NUMBERS[layer]):
            for x in range(0, ODD_NUMBERS[layer]):
                coord_x = (
                    latitude + x - (ODD_NUMBERS[layer] // 2)
                ) % ENCODER_RESOLUTION
                coord_y = (
                    longitude + y - (ODD_NUMBERS[layer] // 2)
                ) % ENCODER_RESOLUTION
                if [coord_x, coord_y] not in search_coords:
                    search_coords.append([coord_x, coord_y])

    return search_coords


def clean_url(url):
    parts = urlsplit(url)
    path = parts.path

    # If path contains a dot, keep only up to the first extension (e.g. .mp3)
    if "." in path:
        # Split path into segments (by /), process the last segment
        segments = path.split("/")
        last_segment = segments[-1]

        # Keep only the part up to the first dot + extension
        first_part = last_segment.split(".")
        if len(first_part) > 1:
            new_last_segment = first_part[0] + "." + first_part[1]
        else:
            new_last_segment = last_segment  # fallback, no change

        # Reassemble path
        segments[-1] = new_last_segment
        new_path = "/".join(segments)
    else:
        new_path = path

    # Reassemble full URL
    new_url = urlunsplit((parts.scheme, parts.netloc, new_path, "", ""))
    return new_url


def Get_Nearby_Cities(latitude: int, longitude: int, fuzziness: int = 7):
    search_coords = Look_Around(latitude, longitude, fuzziness)
    nearby_cities = []
    logging.debug(
        f"Searching at coordinates: [{latitude}, {longitude}] with fuzziness {fuzziness}"
    )
    logging.debug(f"Search area size: {len(search_coords)} coordinates")
    for ref in search_coords:
        index = database.index_map[ref[0]][ref[1]]
        if index != 0xFFFF:
            location = database.Get_Location_By_Index(index)
            if location not in nearby_cities:
                nearby_cities.append(location)
    nearby_cities.sort()
    logging.debug(f"Nearby cities found: {nearby_cities}")
    return nearby_cities


def Back_To_Tuning():
    global state
    global state_entry

    if state != "tuning":
        state = "tuning"
        state_entry = True
        logging.debug("Back to tuning state")


def Clear_Volume_Display():
    global volume_display

    volume_display = False
    logging.debug("Volume display cleared")


def Clear_Mode_Message():
    global state_entry
    state_entry = True
    display_thread.clear()
    logging.debug("Mode message cleared")


def play_first_station(location_name, url_list, stations_list):
    global streamer
    if streamer:
        streamer.stop()
    streamer = Streamer(AUDIO_SERVICE, url_list[0])
    streamer.play()
    logging.info(f"Playing {location_name}, first station: {stations_list[0]}")


def Process_UI_Events():
    global state
    global state_entry
    global volume
    global volume_display
    global jog
    global ui_manager
    global encoders_thread
    global rgb_led
    global current_mode, nearby_cities, coordinates, streamer, last_activity_time

    try:
        ui_events = []
        ui_manager.update(ui_events)
        for event in ui_events:
            if event[0] == "Jog":
                if event[1] == 1:
                    jog = (jog + 1) % 20
                elif event[1] == -1:
                    jog = (jog - 1) % 20
                logging.debug(f"Jog position: {jog}")
                last_activity_time = time.time()

            elif event[0] == "Volume":
                if event[1] == 1:
                    volume += VOLUME_INCREMENT
                    volume_display = True
                    scheduler.attach_timer(Clear_Volume_Display, 3)
                    rgb_led.set_static("RED", timeout_sec=0.5)
                    logging.debug(f"Volume up: {volume}%")
                elif event[1] == -1:
                    if state == "shutdown_confirm":
                        Back_To_Tuning()
                    else:
                        volume -= VOLUME_INCREMENT
                        volume_display = True
                        scheduler.attach_timer(Clear_Volume_Display, 3)
                        rgb_led.set_static("RED", timeout_sec=0.5)
                        logging.debug(f"Volume down: {volume}%")
                last_activity_time = time.time()

            elif event[0] == "Mode_Toggle":
                current_mode = ui_manager.dial.get_mode()
                display_thread.message(
                    line_1=f"Mode: {current_mode.replace('_select', '').capitalize()}",
                    line_2="",
                    line_3="",
                    line_4="",
                )
                coordinates = encoders_thread.get_readings()
                if current_mode == MODE_CITY:
                    rgb_led.set_static("GREEN")
                    if state == "playing":
                        if streamer:
                            streamer.stop()
                            logging.debug("Stopped streamer on mode switch to city")
                        nearby_cities = Get_Nearby_Cities(
                            coordinates[0], coordinates[1]
                        )
                        logging.info(
                            f"Refreshed nearby cities on mode toggle: {nearby_cities}"
                        )
                else:
                    rgb_led.set_static("OFF")
                scheduler.attach_timer(Clear_Mode_Message, 2)
                last_activity_time = time.time()
                logging.info(f"Switched to {current_mode}")

            elif event[0] == "Shutdown":
                state = "shutdown_confirm"
                state_entry = True
                logging.info("Shutdown confirmation triggered")

            elif event[0] == "Calibrate":
                logging.info(f"Calibrate Event: {event[0]} triggered")
                offsets = encoders_thread.zero()
                database.Save_Calibration(offsets[0], offsets[1])
                rgb_led.set_static("GREEN", timeout_sec=0.5)
                display_thread.message(
                    line_1="", line_2="Calibrated!", line_3="", line_4=""
                )
                logging.info("Calibrated")
                time.sleep(1)

            elif event[0] == "Confirm":
                if state == "shutdown_confirm":
                    state = "shutdown"
                    state_entry = True
                    logging.info("Shutdown confirmed")

    except Exception as e:
        logging.error(f"UI event processing failed: {e}")


# PROGRAM START
format = "%(asctime)s: %(message)s"
logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
logging.getLogger().setLevel(logging.DEBUG)

logging.info(f"Starting RadioGlobe v{RADIOGLOBE_VERSION}")

database.Load_Map()

encoder_offsets = database.Load_Calibration()

encoders_thread = Positional_Encoders(
    2, "Encoders", encoder_offsets[0], encoder_offsets[1]
)
encoders_thread.start()
logging.info("Encoders thread started")

display_thread = Display(3, "Display")
display_thread.start()
logging.info("Display thread started")

rgb_led = RGB_LED(20, "RGB_LED")
rgb_led.start()
logging.info("RGB LED thread started")

scheduler = Scheduler(50, "SCHEDULER")
scheduler.start()
logging.info("Scheduler thread started")

ui_manager = UI_Manager()
logging.info("UI manager initialized")

while True:
    try:
        if state == "start":
            if state_entry:
                state_entry = False
                display_thread.message(
                    line_1="Radio Globe",
                    line_2="Made for DesignSpark",
                    line_3="Jude Pullen, Donald",
                    line_4="Robson, Pete Milne",
                )
                scheduler.attach_timer(Back_To_Tuning, 5)
                logging.info("Splash screen displayed")

        elif state == "tuning":
            if state_entry:
                state_entry = False
                rgb_led.set_blink("WHITE")
                display_thread.clear()
                logging.debug("Tuning state entered")
            else:
                coordinates = encoders_thread.get_readings()
                search_area = Look_Around(coordinates[0], coordinates[1], fuzziness=5)
                locations = set()  # Collect unique locations
                for ref in search_area:
                    index = database.index_map[ref[0]][ref[1]]
                    if index != 0xFFFF:
                        location = database.Get_Location_By_Index(index)
                        locations.add(location)

                if locations:
                    if len(locations) == 1:
                        # Only one city found, use it
                        location_name = next(iter(locations))
                    else:
                        # Multiple cities found, select the closest one
                        min_distance_sq = float("inf")
                        closest_location = None
                        for location in locations:
                            # Get city coordinates in degrees
                            city_coords = database.stations_data[location]["coords"]
                            city_lat_deg = city_coords["n"]
                            city_lon_deg = city_coords["e"]
                            # Convert to encoder steps (same as Build_Map)
                            city_lat_center = round(
                                (city_lat_deg + 180) * ENCODER_RESOLUTION / 360
                            )
                            city_lon_center = round(
                                (city_lon_deg + 180) * ENCODER_RESOLUTION / 360
                            )
                            # Calculate distance considering wrap-around
                            lat_diff = min(
                                abs(coordinates[0] - city_lat_center),
                                ENCODER_RESOLUTION
                                - abs(coordinates[0] - city_lat_center),
                            )
                            lon_diff = min(
                                abs(coordinates[1] - city_lon_center),
                                ENCODER_RESOLUTION
                                - abs(coordinates[1] - city_lon_center),
                            )
                            distance_sq = (
                                lat_diff**2 + lon_diff**2
                            )  # Squared distance for comparison
                            if distance_sq < min_distance_sq:
                                min_distance_sq = distance_sq
                                closest_location = location
                        location_name = closest_location

                    # Populate stations only from the selected location
                    stations_list = []
                    url_list = []
                    for station in database.stations_data[location_name]["urls"]:
                        stations_list.append(station["name"])
                        url_list.append(station["url"])
                    encoders_thread.latch(coordinates[0], coordinates[1], stickiness=3)
                    state = "playing"
                    state_entry = True

                latitude = round((360 * coordinates[0] / ENCODER_RESOLUTION - 180), 2)
                longitude = round((360 * coordinates[1] / ENCODER_RESOLUTION - 180), 2)
                volume_disp = volume if volume_display else 0
                display_thread.update(
                    latitude, longitude, "Tuning...", volume_disp, "", False
                )
                # logging.debug(f"Tuning: lat={latitude}, lon={longitude}")

        elif state == "playing":
            if state_entry:
                state_entry = False
                nearby_cities = Get_Nearby_Cities(coordinates[0], coordinates[1])
                current_city_index = (
                    0 if not nearby_cities else nearby_cities.index(location_name)
                )
                if current_mode == MODE_STATION:
                    jog = 0  # Ensure first station plays in MODE_STATION
                else:
                    jog = current_city_index  # Use city index in MODE_CITY
                last_jog = jog - 1
                latitude = database.stations_data[location_name]["coords"]["n"]
                longitude = database.stations_data[location_name]["coords"]["e"]
                play_first_station(location_name, url_list, stations_list)
                if current_mode == MODE_CITY:
                    rgb_led.set_static("GREEN")
                else:
                    rgb_led.set_static("OFF")
                last_activity_time = time.time()

            elif not encoders_thread.is_latched():
                if streamer:
                    streamer.stop()
                state = "tuning"
                state_entry = True
                logging.debug("Unlatched, returning to tuning")

            elif jog != last_jog:
                last_jog = jog
                if current_mode == MODE_STATION:
                    jog %= len(stations_list)
                    if streamer:
                        streamer.stop()
                    streamer = Streamer(AUDIO_SERVICE, url_list[jog])
                    streamer.play()
                    logging.debug(f"Station changed: {stations_list[jog]}")
                elif current_mode == MODE_CITY:
                    if nearby_cities:
                        total_cities = len(nearby_cities)
                        current_city_index = jog % total_cities
                        new_location_name = nearby_cities[current_city_index]
                        if new_location_name != location_name:
                            location_name = new_location_name
                            stations_list = [
                                station["name"]
                                for station in database.stations_data[location_name][
                                    "urls"
                                ]
                            ]
                            url_list = [
                                station["url"]
                                for station in database.stations_data[location_name][
                                    "urls"
                                ]
                            ]
                            play_first_station(location_name, url_list, stations_list)
                            latitude = database.stations_data[location_name]["coords"][
                                "n"
                            ]
                            longitude = database.stations_data[location_name]["coords"][
                                "e"
                            ]
                            jog = current_city_index
                            last_jog = jog - 1
                            logging.debug(
                                f"City changed: {location_name} (index {current_city_index})"
                            )

            else:
                volume_disp = volume if volume_display else 0
                if current_mode == MODE_STATION and len(stations_list) > 1:
                    display_thread.update(
                        latitude,
                        longitude,
                        location_name,
                        volume_disp,
                        stations_list[jog % len(stations_list)],
                        True,
                    )
                else:
                    display_thread.update(
                        latitude,
                        longitude,
                        location_name,
                        volume_disp,
                        stations_list[jog % len(stations_list)],
                        False,
                    )

            if current_mode == MODE_CITY and last_activity_time > 0:
                current_time = time.time()
                if current_time - last_activity_time >= 3:
                    current_mode = MODE_STATION
                    rgb_led.set_static("OFF")
                    display_thread.message(
                        line_1="Mode: Station", line_2="", line_3="", line_4=""
                    )
                    jog = 0
                    last_jog = -1
                    play_first_station(location_name, url_list, stations_list)
                    scheduler.attach_timer(Clear_Mode_Message, 1)
                    logging.info("City mode timed out, reverted to station_select")
                    last_activity_time = 0

        elif state == "shutdown_confirm":
            if state_entry:
                state_entry = False
                display_thread.clear()
                time.sleep(0.1)
                display_thread.message(
                    line_1="Really shut down?",
                    line_2="<- Press mid button ",
                    line_3="to confirm or",
                    line_4="<- bottom to cancel.",
                )
                scheduler.attach_timer(Back_To_Tuning, 5)
                logging.info("Shutdown confirm displayed")

        elif state == "shutdown":
            if state_entry:
                state_entry = False
                display_thread.clear()
                time.sleep(0.1)
                display_thread.message(
                    line_1="Shutting down...",
                    line_2="Please wait 10 sec",
                    line_3="before disconnecting",
                    line_4="power.",
                )
                subprocess.run(["sudo", "poweroff"])
                logging.info("Shutting down")

        else:
            state = "tuning"
            logging.debug("Defaulted to tuning state")

        Process_UI_Events()
        time.sleep(0.1)

    except Exception as e:
        logging.error(f"Inner main loop failed: {e}")
        time.sleep(1)
