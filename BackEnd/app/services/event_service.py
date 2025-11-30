# services/event_service.py
from typing import List, Dict
from ..db import get_connection

def log_event(
    pump_status: str | None = None,
    servo_position: str | None = None,
    source: str = "system",
    message: str = "",
) -> None:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO actuator_events (pump_status, servo_position, source, message)
        VALUES (?, ?, ?, ?)
    """, (pump_status, servo_position, source, message))
    conn.commit()
    conn.close()

def get_logs(limit: int = 50) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, pump_status, servo_position, source, message
        FROM actuator_events
        ORDER BY id DESC LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "timestamp": r["timestamp"],
            "pump_status": r["pump_status"],
            "servo_position": r["servo_position"],
            "source": r["source"],
            "message": r["message"],
        }
        for r in rows
    ]
