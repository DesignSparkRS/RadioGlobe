import json
import os.path
import subprocess
import logging
import hashlib
import radio_config
from positional_encoders import ENCODER_RESOLUTION


os.makedirs(radio_config.DATADIR, exist_ok=True)


def generate_stations_dict(filename: str) -> dict:
    # Load stations database
    try:
        with open(filename, "r", encoding="utf8") as stations_file:
            stations_dict = json.load(stations_file)
        logging.info(f"Generating stations dictionary from {filename}")
    except FileNotFoundError:
        logging.info(f"{filename} not found")

    return stations_dict


def Get_Location_By_Index(index: int):
    stations_data = generate_stations_dict(radio_config.STATIONS_JSON)
    for idx, location in enumerate(stations_data):
        if idx == index:
            logging.debug(f"{idx}, {location}")
            return location

    return "Unknown"


def get_checksum(filename: str) -> str:
    """Return md5 checksum of file or empty string"""
    checksum = ""
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            data = f.read()
            checksum = hashlib.md5(data).hexdigest()
    logging.debug(f"{filename} Checksum: {checksum}")
    return checksum


def Build_Map(stations_json: str, stations_map: str):
    # Make a map representing every possible coordinate, with a 2-byte address for looking up the city, which
    # allows looking up the stations from the regular database.  This reduces the memory required to hold the map
    # to 2 MiB RAM and because the empty space is all 0xFF it can be compressed very easily if desired to just the
    # locations
    index_map = [[0xFFFF for longd in range(0, ENCODER_RESOLUTION)] for lat in range(0, ENCODER_RESOLUTION)]

    # Load stations database
    stations_data = generate_stations_dict(stations_json)

    # Parse every location
    for idx, location in enumerate(stations_data):
        # Turn the coordinates into indexes for the map.  We need to shift all the numbers to make everything positive
        latitude = round((stations_data[location]["coords"]["n"] + 180) * ENCODER_RESOLUTION / 360)
        longitude = round((stations_data[location]["coords"]["e"] + 180) * ENCODER_RESOLUTION / 360)
        index_map[latitude][longitude] = idx

    # Save the location of each actual location - 2 bytes for latitude, 2 for longitude, 2 for the index
    index_bytes = bytes()
    for lat in range(0, ENCODER_RESOLUTION):
        for lon in range(0, ENCODER_RESOLUTION):
            if index_map[lat][lon] != 0xFFFF:
                index_bytes += bytes([lat & 0xFF,
                                      (lat >> 8) & 0xFF,
                                      lon & 0xFF,
                                      (lon >> 8) & 0xFF,
                                      index_map[lat][lon] & 0xFF,
                                      (index_map[lat][lon] >> 8) & 0xFF])

    # Save the locations to a file
    with open(stations_map, "wb") as locations_file:
        locations_file.write(index_bytes)
        logging.info(f"Saving map {stations_map}")


# def Rebuild_Map():
    # logging.info("Rebuilding map...")
    # index_map = Build_Map(radio_config.STATIONS_JSON)

    # # Save the location of each actual location - 2 bytes for latitude, 2 for longitude, 2 for the index
    # index_bytes = bytes()
    # for lat in range(0, ENCODER_RESOLUTION):
        # for lon in range(0, ENCODER_RESOLUTION):
            # if index_map[lat][lon] != 0xFFFF:
                # index_bytes += bytes([lat & 0xFF,
                                      # (lat >> 8) & 0xFF,
                                      # lon & 0xFF,
                                      # (lon >> 8) & 0xFF,
                                      # index_map[lat][lon] & 0xFF,
                                      # (index_map[lat][lon] >> 8) & 0xFF])

    # # Save the locations to a file
    # with open(radio_config.STATIONS_MAP, "wb") as locations_file:
        # locations_file.write(index_bytes)
        # logging.info(f"Saving map {radio_config.STATIONS_MAP}")

    # # checksums = Get_Checksums()
    # # with open(radio_config.CHECKSUMS_JSON, "w") as checksum_file:
        # # checksum_file.write(json.dumps(checksums))
        # # logging.info(f"Saving checksums {radio_config.CHECKSUMS_JSON}")


def Load_Map(filename: str) -> list:
    # try:
        # checksums = Get_Checksums()
        # with open(radio_config.CHECKSUMS_JSON, "r") as checksum_file:
            # saved_checksums = json.load(checksum_file)
    # except json.decoder.JSONDecodeError:
        # Build_Map()
        # return
    # except FileNotFoundError:
        # Build_Map()
        # return

    # Check the md5 of the database, to see if the current map is still valid
    # if checksums["database"] != saved_checksums["database"]:
        # Build_Map()
        # return

    # Check the md5 of the map, to see if it's valid
    # if checksums["map"] != saved_checksums["map"]:
        # Build_Map()
        # return

    # Load the map data file
    index_bytes = None
    try:
        with open(filename, "rb") as map_file:
            index_bytes = map_file.read()
            logging.debug(f"{filename} loaded...")
    except FileNotFoundError:
        logging.debug(f"{filename} not found")

    # Ensure index_map is empty first
    index_map = [[0xFFFF for longd in range(0, ENCODER_RESOLUTION)] for lat in range(0, ENCODER_RESOLUTION)]

    # Load the locations from the data file - each is represented by 6 bytes as detailed in Save_Map
    byte = 0
    while byte < len(index_bytes):
        lat = (index_bytes[byte + 1] << 8) | index_bytes[byte]
        lon = (index_bytes[byte + 3] << 8) | index_bytes[byte + 2]
        value = (index_bytes[byte + 5] << 8) | index_bytes[byte + 4]
        byte += 6
        index_map[lat][lon] = value
    return index_map


def Save_Calibration(latitude: int, longitude: int):
    offsets = [latitude, longitude]
    with open(radio_config.OFFSETS_JSON, "w") as offsets_file:
        offsets_file.write(json.dumps(offsets))
        logging.debug(f"{radio_config.OFFSETS_JSON} saved...")


def Load_Calibration():
    try:
        with open(radio_config.OFFSETS_JSON, "r") as offsets_file:
            offsets = json.load(offsets_file)
    except Exception:
        offsets = [0, 0]

    logging.debug(f"Setting offsets to: {offsets}")

    return offsets


if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO, datefmt="%H:%M:%S")
    logging.getLogger().setLevel(logging.DEBUG)

    generate_stations_dict(radio_config.STATIONS_JSON)
    Get_Location_By_Index(0)
    get_checksum(radio_config.STATIONS_JSON)
    Build_Map(radio_config.STATIONS_JSON, radio_config.STATIONS_MAP)
    # Rebuild_Map()
    Load_Map(radio_config.STATIONS_MAP)

    # for lat in range(ENCODER_RESOLUTION):
        # for lon in range(ENCODER_RESOLUTION):
            # if index_map[lat][lon] != 0xFFFF:
                # print("OUT", lat, lon, index_map[lat][lon])
