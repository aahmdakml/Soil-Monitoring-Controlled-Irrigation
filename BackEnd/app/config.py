# app/config.py
from pathlib import Path

# Lokasi file DB (SQLite)
DB_PATH = Path(__file__).resolve().parent.parent / "watering_server.db"

# Default device id (kalau nanti multi-raspi, bisa ditambah)
DEFAULT_DEVICE_ID = "raspi-1"
