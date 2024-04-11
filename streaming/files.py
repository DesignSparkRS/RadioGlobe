# utils/files.py
import json


def load_stations(file: str) -> dict:
    with open(file, 'r', encoding='utf8') as f:
        stations = json.load(f)
        return stations