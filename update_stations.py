#!/usr/bin/python

"""
Add / update stations

Can be used to add and update the stations json file.

1. If the city doesn't exist, then it will be added along with its station data

2. If the city exists any new stations will be added to the list of stations

3. If the city & station name exists, the station URL will be updated

Note: Updating station names is not supported as these are used as the key

*** The update file must be valid json in the the staions.json format ***

Usage: update_stations <stations_json> <new_stations_json>
eg: update_stations 'json/stations.json' 'json/new_stations.json'

"""

import json


def run(stations_json, new_stations_json):

    # Get stations dict
    with open(stations_json, "r") as read_file:
        stations_dict = json.load(read_file)

    # Get new stations dict
    with open(new_stations_json, "r") as read_file:
        new_stations_dict = json.load(read_file)

    for city, data in new_stations_dict.items():
        # If city dosen't exist in stations, add it along with all the data
        if city not in stations_dict:
            print("Adding City: ", city)
            stations_dict[city] = data
        # If city is already in stations...
        else:
            print("Updating stations...")
            for station in data["urls"]:
                names_list = [station["name"] for station in stations_dict[city]["urls"]]
                print(names_list)
                print("Checking station name: ", station["name"])
                # Add new stations to city
                if station["name"] not in names_list:
                    print("Adding new station: ", station)
                    stations_dict[city]["urls"].append(station)
                # Update the station URL - updating station name is not supported as it's the key
                else:
                    for s in stations_dict[city]["urls"]:
                        if s["name"] == station["name"]:
                            print("Updating station URL: ", s["name"], s["url"])
                            s["url"] = station["url"]

    with open(stations_json, 'w', encoding='utf8') as f:
        json.dump(stations_dict, f, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    import sys

    stations_file = sys.argv[1]
    new_stations_file = sys.argv[2]

    run(stations_file, new_stations_file)
