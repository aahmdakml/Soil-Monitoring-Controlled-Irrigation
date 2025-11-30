# app/db.py
import sqlite3
from pathlib import Path
from .config import DB_PATH, DEFAULT_DEVICE_ID

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize SQLite database with all tables & indexes."""
    # pastikan foldernya ada
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = get_conn()
    c = conn.cursor()

    # devices
    c.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id   TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            description TEXT,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # sensor readings (time-series)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id     TEXT NOT NULL,
            timestamp     DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperature   REAL,
            humidity      REAL,
            light         REAL,
            soil_moisture REAL,
            FOREIGN KEY (device_id) REFERENCES devices(device_id)
        )
    """)


    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_sensor_device_time
        ON sensor_readings (device_id, timestamp DESC)
    """)

    # actuator events (pump / servo / schedule logs)
    c.execute("""
        CREATE TABLE IF NOT EXISTS actuator_events (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id      TEXT NOT NULL,
            timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,
            pump_status    TEXT,
            servo_position TEXT,
            source         TEXT,
            message        TEXT,
            command_id     INTEGER,
            FOREIGN KEY (device_id) REFERENCES devices(device_id)
        )
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_events_device_time
        ON actuator_events (device_id, timestamp DESC)
    """)

    # watering schedule (config per device)
    c.execute("""
        CREATE TABLE IF NOT EXISTS watering_schedule (
            device_id          TEXT PRIMARY KEY,
            enabled            INTEGER NOT NULL DEFAULT 0,
            time_hhmm          TEXT NOT NULL,
            duration_seconds   INTEGER NOT NULL,
            moisture_threshold REAL NOT NULL,
            updated_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES devices(device_id)
        )
    """)

    # commands queue (FE → edge)
    c.execute("""
        CREATE TABLE IF NOT EXISTS commands (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id  TEXT NOT NULL,
            type       TEXT NOT NULL,
            payload    TEXT NOT NULL,
            status     TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            sent_at    DATETIME,
            done_at    DATETIME,
            FOREIGN KEY (device_id) REFERENCES devices(device_id)
        )
    """)

    c.execute("""
        CREATE INDEX IF NOT EXISTS idx_commands_device_status
        ON commands (device_id, status, created_at)
    """)

    # seed default device & schedule bila belum ada
    c.execute("SELECT COUNT(*) AS cnt FROM devices")
    if c.fetchone()["cnt"] == 0:
        c.execute(
            "INSERT INTO devices (device_id, name, description) VALUES (?, ?, ?)",
            (DEFAULT_DEVICE_ID, "Raspberry Pi #1", "Default edge device"),
        )

    c.execute(
        "SELECT COUNT(*) AS cnt FROM watering_schedule WHERE device_id = ?",
        (DEFAULT_DEVICE_ID,),
    )
    if c.fetchone()["cnt"] == 0:
        c.execute("""
            INSERT INTO watering_schedule
                (device_id, enabled, time_hhmm, duration_seconds, moisture_threshold)
            VALUES (?, ?, ?, ?, ?)
        """, (DEFAULT_DEVICE_ID, 0, "06:00", 30, 300.0))

    conn.commit()
    conn.close()
