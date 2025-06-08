#! /usr/bin/python3
import json
import os
import subprocess
from positional_encoders import ENCODER_RESOLUTION
import logging

stations_data = {}

# Make a map representing every possible coordinate, with a 2-byte address for looking up the city, which
# allows looking up the stations from the regular database.  This reduces the memory required to hold the map
# to 2 MiB RAM and because the empty space is all 0xFF it can be compressed very easily if desired to just the
# locations
index_map = [
    [0xFFFF for longd in range(0, ENCODER_RESOLUTION)]
    for lat in range(0, ENCODER_RESOLUTION)
]


def Get_Location_By_Index(index: int):
    global stations_data

    if stations_data == {}:
        # Load stations database
        try:
            with open("stations.json", "r") as stations_file:
                stations_data = json.load(stations_file)
            logging.info("Stations data loaded")
        except Exception as e:
            logging.error(f"Failed to load stations.json: {e}")
            raise
    for loc, idx in enumerate(stations_data.keys()):
        if loc == index:
            return idx
    return "Unknown location"


def Get_Checksums():
    # Produce md5s of the database, so changes can be detected, and the map so corruption can be detected
    checksums = {}
    try:
        md5 = subprocess.run(
            ["md5sum", "stations.json"], stdout=subprocess.PIPE, check=True
        )
        checksums["database"] = (
            str(md5.stdout, encoding="utf8").strip().split()[0]
        )  # Only the hash
    except Exception as e:
        logging.error(f"Failed to get stations.json checksum: {e}")
        checksums["database"] = "unknown"
    return checksums  # Only checksum stations.json, not map.dat


def Build_Map():
    global index_map, stations_data
    logging.info("Rebuilding map from stations.json")
    try:
        with open("stations.json", "r") as stations_file:
            stations_data = json.load(stations_file)
    except FileNotFoundError:
        logging.error("stations.json not found. Terminating.")
        exit(1)

    # Parse every location
    location_index = 0
    for location in stations_data:
        lat_center = round(
            (stations_data[location]["coords"]["n"] + 180) * ENCODER_RESOLUTION / 360
        )
        lon_center = round(
            (stations_data[location]["coords"]["e"] + 180) * ENCODER_RESOLUTION / 360
        )
        for lat_offset in range(-2, 3):
            for lon_offset in range(-2, 3):
                lat = (lat_center + lat_offset) % ENCODER_RESOLUTION
                lon = (lon_center + lon_offset) % ENCODER_RESOLUTION
                index_map[lat][lon] = location_index
                if location == "Dover,US-DE":
                    logging.debug(
                        f"Indexed Dover,US-DE at [{lat}, {lon}] with index {location_index}"
                    )
        location_index += 1

    Save_Map()


def Save_Map():
    global index_map
    logging.info("Saving map to data/map.dat")
    index_bytes = bytes()
    for lat in range(0, ENCODER_RESOLUTION):
        for lon in range(0, ENCODER_RESOLUTION):
            if index_map[lat][lon] != 0xFFFF:
                index_bytes += bytes(
                    [
                        lat & 0xFF,
                        (lat >> 8) & 0xFF,
                        lon & 0xFF,
                        (lon >> 8) & 0xFF,
                        index_map[lat][lon] & 0xFF,
                        (index_map[lat][lon] >> 8) & 0xFF,
                    ]
                )

    # Save the locations to a file
    os.makedirs("data", exist_ok=True)
    try:
        with open("data/map.dat", "wb") as locations_file:
            locations_file.write(index_bytes)
        checksums = Get_Checksums()
        with open("data/checksums.json", "w") as checksum_file:
            checksum_file.write(json.dumps(checksums))
        logging.info("Map saved successfully")
    except Exception as e:
        logging.error(f"Failed to save map: {e}")


def Load_Map():
    global index_map
    current_checksums = Get_Checksums()
    try:
        with open("data/checksums.json", "r") as checksum_file:
            saved_checksums = json.load(checksum_file)
    except (json.JSONDecodeError, FileNotFoundError):
        logging.warning("Checksums not found, rebuilding map")
        Build_Map()
        return

    # Only check stations.json checksum, rebuild if it differs
    if current_checksums["database"] != saved_checksums.get("database", "unknown"):
        logging.warning("stations.json checksum mismatch, rebuilding map")
        Build_Map()
        return

    # Load the map data file
    try:
        with open("data/map.dat", "rb") as map_file:
            index_bytes = map_file.read()
    except FileNotFoundError:
        logging.warning("Map file not found, rebuilding map")
        Build_Map()
        return

    # Ensure index_map is empty first
    index_map = [
        [0xFFFF for longd in range(0, ENCODER_RESOLUTION)]
        for lat in range(0, ENCODER_RESOLUTION)
    ]

    # Load the locations from the data file - each is represented by 6 bytes as detailed in Save_Map
    byte = 0
    while byte < len(index_bytes):
        lat = (index_bytes[byte + 1] << 8) | index_bytes[byte]
        lon = (index_bytes[byte + 3] << 8) | index_bytes[byte + 2]
        value = (index_bytes[byte + 5] << 8) | index_bytes[byte + 4]
        byte += 6
        index_map[lat][lon] = value
    logging.info("Map loaded successfully from data/map.dat")


def Save_Calibration(latitude: int, longitude: int):
    offsets = [latitude, longitude]
    try:
        with open("data/offsets.json", "w") as offsets_file:
            offsets_file.write(json.dumps(offsets))
        logging.debug("Calibration saved")
    except Exception as e:
        logging.error(f"Failed to save calibration: {e}")


def Load_Calibration():
    try:
        with open("data/offsets.json", "r") as offsets_file:
            offsets = json.load(offsets_file)
        logging.debug("Calibration loaded")
    except Exception as e:
        logging.warning(f"Calibration load failed: {e}, using defaults")
        offsets = [0, 0]

    return offsets


if __name__ == "__main__":
    Load_Map()
    Save_Map()

    for lat in range(ENCODER_RESOLUTION):
        for lon in range(ENCODER_RESOLUTION):
            if index_map[lat][lon] != 0xFFFF:
                print("OUT", lat, lon, index_map[lat][lon])
