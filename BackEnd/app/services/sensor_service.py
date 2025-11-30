# services/sensor_service.py
from typing import List, Dict, Optional
from ..db import get_connection

def insert_sensor(humidity: float, light: float, soil_moisture: float) -> None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO sensor_readings (humidity, light, soil_moisture)
        VALUES (?, ?, ?)
    """, (humidity, light, soil_moisture))
    conn.commit()
    conn.close()

def get_latest_sensor() -> Optional[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, humidity, light, soil_moisture
        FROM sensor_readings
        ORDER BY id DESC LIMIT 1
    """)
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "timestamp": row["timestamp"],
        "humidity": row["humidity"],
        "light": row["light"],
        "soil_moisture": row["soil_moisture"],
    }

def get_history(limit: int = 50) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, humidity, light, soil_moisture
        FROM sensor_readings
        ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "timestamp": r["timestamp"],
            "humidity": r["humidity"],
            "light": r["light"],
            "soil_moisture": r["soil_moisture"],
        }
        for r in rows
    ]
