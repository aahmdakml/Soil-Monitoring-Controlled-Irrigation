# app/crud.py
import json
from typing import List, Dict, Optional
from .db import get_conn
from .config import DEFAULT_DEVICE_ID
from .schemas import ScheduleRequest, CommandOut

# ----- SENSOR DATA -----
def get_latest_sensor(device_id: str = DEFAULT_DEVICE_ID) -> Optional[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, temperature, humidity, light, soil_moisture
        FROM sensor_readings
        WHERE device_id = ?
        ORDER BY id DESC LIMIT 1
    """, (device_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "timestamp": row["timestamp"],
        "temperature": row["temperature"],
        "humidity": row["humidity"],
        "light": row["light"],
        "soil_moisture": row["soil_moisture"],
    }


def get_history(device_id: str = DEFAULT_DEVICE_ID, limit: int = 50) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, temperature, humidity, light, soil_moisture
        FROM sensor_readings
        WHERE device_id = ?
        ORDER BY id DESC LIMIT ?
    """, (device_id, limit))
    rows = c.fetchall()
    conn.close()
    return [
        {
            "timestamp": r["timestamp"],
            "temperature": r["temperature"],
            "humidity": r["humidity"],
            "light": r["light"],
            "soil_moisture": r["soil_moisture"],
        }

        for r in rows
    ]

# ----- LOGS -----
def get_logs(device_id: str = DEFAULT_DEVICE_ID, limit: int = 50) -> List[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, pump_status, servo_position, source, message
        FROM actuator_events
        WHERE device_id = ?
        ORDER BY id DESC LIMIT ?
    """, (device_id, limit))
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

# ----- SCHEDULE -----
def get_schedule(device_id: str = DEFAULT_DEVICE_ID) -> Optional[Dict]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT enabled, time_hhmm, duration_seconds, moisture_threshold
        FROM watering_schedule
        WHERE device_id = ?
    """, (device_id,))
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

def update_schedule(device_id: str, sched: ScheduleRequest):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO watering_schedule (device_id, enabled, time_hhmm, duration_seconds, moisture_threshold)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(device_id) DO UPDATE SET
            enabled = excluded.enabled,
            time_hhmm = excluded.time_hhmm,
            duration_seconds = excluded.duration_seconds,
            moisture_threshold = excluded.moisture_threshold
    """, (
        device_id,
        1 if sched.enabled else 0,
        sched.time_hhmm,
        sched.duration_seconds,
        sched.moisture_threshold,
    ))
    conn.commit()
    conn.close()

# ----- COMMANDS QUEUE -----
def enqueue_command(device_id: str, cmd_type: str, payload: dict):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO commands (device_id, type, payload, status)
        VALUES (?, ?, ?, 'pending')
    """, (device_id, cmd_type, json.dumps(payload)))
    conn.commit()
    conn.close()

def get_pending_commands(device_id: str = DEFAULT_DEVICE_ID) -> List[CommandOut]:
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, type, payload
        FROM commands
        WHERE device_id = ? AND status = 'pending'
        ORDER BY id ASC
    """, (device_id,))
    rows = c.fetchall()
    ids = [r["id"] for r in rows]
    if ids:
        c.execute(
            f"UPDATE commands SET status = 'sent' WHERE id IN ({','.join('?' for _ in ids)})",
            ids
        )
    conn.commit()
    conn.close()

    cmds: List[CommandOut] = []
    for r in rows:
        try:
            payload = json.loads(r["payload"])
        except Exception:
            payload = {}
        cmds.append(CommandOut(id=r["id"], type=r["type"], payload=payload))
    return cmds

def mark_command_done(command_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE commands SET status = 'done' WHERE id = ?", (command_id,))
    conn.commit()
    conn.close()
