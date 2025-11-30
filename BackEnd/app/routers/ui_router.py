# app/routers/ui_router.py
from fastapi import APIRouter, HTTPException
from ..config import DEFAULT_DEVICE_ID
from ..schemas import PumpRequest, ServoRequest, ScheduleRequest
from ..crud import (
    get_latest_sensor,
    get_history,
    get_logs,
    get_schedule,
    update_schedule,
    enqueue_command,
)
from ..db import get_conn

router = APIRouter(prefix="/api", tags=["ui"])

@router.get("/status")
def api_status(device_id: str = DEFAULT_DEVICE_ID):
    sensor = get_latest_sensor(device_id)
    sched = get_schedule(device_id)

    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT pump_status, servo_position
        FROM actuator_events
        WHERE device_id = ?
        ORDER BY id DESC LIMIT 1
    """, (device_id,))
    row = c.fetchone()
    conn.close()

    pump_status = row["pump_status"] if row and row["pump_status"] else "off"
    servo_position = row["servo_position"] if row and row["servo_position"] else "close"

    return {
        "sensor": sensor,
        "pump_status": pump_status,
        "servo_position": servo_position,
        "schedule": sched,
    }

@router.get("/history")
def api_history(limit: int = 50, device_id: str = DEFAULT_DEVICE_ID):
    return get_history(device_id, limit)

@router.get("/logs")
def api_logs(limit: int = 50, device_id: str = DEFAULT_DEVICE_ID):
    return get_logs(device_id, limit)

@router.get("/schedule")
def api_get_schedule(device_id: str = DEFAULT_DEVICE_ID):
    return get_schedule(device_id)

@router.post("/schedule")
def api_set_schedule(req: ScheduleRequest, device_id: str = DEFAULT_DEVICE_ID):
    update_schedule(device_id, req)
    return {"ok": True, "schedule": get_schedule(device_id)}

@router.post("/pump")
def api_pump(req: PumpRequest, device_id: str = DEFAULT_DEVICE_ID):
    if req.status not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="status must be 'on' or 'off'")
    enqueue_command(device_id, "pump", {"status": req.status})

    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO actuator_events (device_id, pump_status, servo_position, source, message)
        VALUES (?, ?, NULL, ?, ?)
    """, (device_id, req.status, "user", f"Pump command '{req.status}' queued"))
    conn.commit()
    conn.close()

    return {"ok": True, "queued": True}

@router.post("/servo")
def api_servo(req: ServoRequest, device_id: str = DEFAULT_DEVICE_ID):
    if req.position not in ["open", "half", "close"]:
        raise HTTPException(status_code=400, detail="position must be 'open', 'half', or 'close'")
    enqueue_command(device_id, "servo", {"position": req.position})

    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO actuator_events (device_id, pump_status, servo_position, source, message)
        VALUES (?, NULL, ?, ?, ?)
    """, (device_id, req.position, "user", f"Servo command '{req.position}' queued"))
    conn.commit()
    conn.close()

    return {"ok": True, "queued": True}
