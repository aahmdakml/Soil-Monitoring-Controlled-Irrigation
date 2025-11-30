# serial_reader.py
import threading
import time
import json
import serial
from .config import SERIAL_PORT, SERIAL_BAUD
from .services.sensor_service import insert_sensor

def _serial_loop():
    print(f"[SERIAL] Trying to open {SERIAL_PORT} @ {SERIAL_BAUD}")
    while True:
        try:
            with serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=1) as ser:
                print("[SERIAL] Port opened.")
                while True:
                    line = ser.readline().decode(errors="ignore").strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        h = data.get("humidity")
                        l = data.get("light")
                        s = data.get("soil_moisture")
                        if h is not None and l is not None and s is not None:
                            insert_sensor(float(h), float(l), float(s))
                    except json.JSONDecodeError:
                        print("[SERIAL] Invalid JSON:", line)
        except Exception as e:
            print("[SERIAL] Error:", e)
            time.sleep(5)

def start_serial_reader():
    t = threading.Thread(target=_serial_loop, daemon=True)
    t.start()
