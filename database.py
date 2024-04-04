import json
import os
import subprocess
from positional_encoders import ENCODER_RESOLUTION

stations_data = {}

# Make a map representing every possible coordinate, with a 2-byte address for looking up the city, which
# allows looking up the stations from the regular database.  This reduces the memory required to hold the map
# to 2 MiB RAM and because the empty space is all 0xFF it can be compressed very easily if desired to just the
# locations
index_map = [[0xFFFF for longd in range(0, ENCODER_RESOLUTION)] for lat in range(0, ENCODER_RESOLUTION)]


def Get_Location_By_Index(index: int):
    global stations_data

    if stations_data == {}:
        # Load stations database
        try:
            stations_file = open("stations.json", "r")
            stations_data = json.load(stations_file)
            stations_file.close()
        except FileNotFoundError:
            print("./stations.json not found.  Terminating.")
            exit()

    i = 0
    for location in stations_data:
        if i == index:
            return location
        i += 1

    return "Unknown location"


def Get_Checksums():
    # Produce md5s of the database, so changes can be detected, and the map so corruption can be detected
    checksums = {}
    md5 = subprocess.run(["md5sum", "stations.json"], stdout=subprocess.PIPE)
    checksums["database"] = str(md5.stdout, encoding="utf8").strip()

    md5 = None
    md5 = subprocess.run(["md5sum", "data/map.dat"], stdout=subprocess.PIPE)
    checksums["map"] = str(md5.stdout, encoding="utf8").strip()

    return checksums


def Build_Map():
    global index_map
    global stations_data

    print("Rebuilding map")

    # Load stations database
    try:
        stations_file = open("stations.json", "r")
        stations_data = json.load(stations_file)
        stations_file.close()
    except FileNotFoundError:
        print("./stations.json not found.  Terminating.")
        exit()

    # Parse every location
    location_index = 0
    for location in stations_data:
        # Turn the coordinates into indexes for the map.  We need to shift all the numbers to make everything positive
        latitude = round((stations_data[location]["coords"]["n"] + 180) * ENCODER_RESOLUTION / 360)
        longitude = round((stations_data[location]["coords"]["e"] + 180) * ENCODER_RESOLUTION / 360)

        # Record the index of the location in the map
        index_map[latitude][longitude] = location_index
        location_index += 1

    Save_Map()


def Save_Map():
    global index_map

    print("Saving map")

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
    os.makedirs("data", exist_ok=True)
    locations_file = open("data/map.dat", "wb")
    locations_file.write(index_bytes)
    locations_file.close()

    checksums = Get_Checksums()
    checksum_file = open("data/checksums.json", "w")
    checksum_file.write(json.dumps(checksums))
    checksum_file.close()

    print("Done")


def Load_Map():
    global index_map

    try:
        checksums = Get_Checksums()
        checksum_file = open("data/checksums.json", "r")
        saved_checksums = json.load(checksum_file)
        checksum_file.close()
    except json.decoder.JSONDecodeError:
        Build_Map()
        return
    except FileNotFoundError:
        Build_Map()
        return

    # Check the md5 of the database, to see if the current map is still valid
    if checksums["database"] != saved_checksums["database"]:
        Build_Map()
        return

    # Check the md5 of the map, to see if it's valid
    if checksums["map"] != saved_checksums["map"]:
        Build_Map()
        return

    # Load the map data file
    try:
        map_file = open("data/map.dat", "rb")
        index_bytes = map_file.read()
        map_file.close()
    except FileNotFoundError:
        Load_Map()
        return

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


def Save_Calibration(latitude: int, longitude: int):
    offsets = [latitude, longitude]
    offsets_file = open("data/offsets.json", "w")
    offsets_file.write(json.dumps(offsets))
    offsets_file.close()


def Load_Calibration():
    try:
        offsets_file = open("data/offsets.json", "r")
        offsets = json.load(offsets_file)
        offsets_file.close()
    except Exception:
        offsets = [0, 0]

    return offsets


if __name__ == "__main__":
    Load_Map()
    Save_Map()

    for lat in range(ENCODER_RESOLUTION):
        for lon in range(ENCODER_RESOLUTION):
            if index_map[lat][lon] != 0xFFFF:
                print("OUT", lat, lon, index_map[lat][lon])
