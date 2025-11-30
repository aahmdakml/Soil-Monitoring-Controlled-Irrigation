# services/scheduler_service.py
import threading
import time
from datetime import datetime
from typing import Optional, Dict
from ..db import get_connection
from ..config import SCHEDULER_INTERVAL_SEC
from .sensor_service import get_latest_sensor
from .gpio_service import set_pump
from .event_service import log_event

def get_schedule() -> Optional[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT enabled, time_hhmm, duration_seconds, moisture_threshold
        FROM watering_schedule
        WHERE id = 1
    """)
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "enabled": bool(row["enabled"]),
        "time_hhmm": row["time_hhmm"],
        "duration_seconds": row["duration_seconds"],
        "moisture_threshold": row["moisture_threshold"],
    }

def update_schedule(enabled: bool, time_hhmm: str, duration_seconds: int, moisture_threshold: float):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE watering_schedule
        SET enabled=?, time_hhmm=?, duration_seconds=?, moisture_threshold=?
        WHERE id=1
    """, (1 if enabled else 0, time_hhmm, duration_seconds, moisture_threshold))
    conn.commit()
    conn.close()
    log_event(source="user", message="Schedule updated")

def _scheduler_loop():
    print("[SCHEDULER] Started.")
    while True:
        try:
            sched = get_schedule()
            sensor = get_latest_sensor()
            if sched and sched["enabled"] and sensor:
                now_hhmm = datetime.now().strftime("%H:%M")
                if now_hhmm == sched["time_hhmm"] and sensor["soil_moisture"] > sched["moisture_threshold"]:
                    # auto watering event
                    log_event(source="auto", message="Auto watering triggered")
                    set_pump("on", source="auto")
                    time.sleep(sched["duration_seconds"])
                    set_pump("off", source="auto")
            time.sleep(SCHEDULER_INTERVAL_SEC)
        except Exception as e:
            print("[SCHEDULER] Error:", e)
            time.sleep(SCHEDULER_INTERVAL_SEC)

def start_scheduler():
    t = threading.Thread(target=_scheduler_loop, daemon=True)
    t.start()

