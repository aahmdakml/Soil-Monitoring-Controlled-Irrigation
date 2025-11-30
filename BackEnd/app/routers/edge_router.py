# app/routers/edge_router.py
from fastapi import APIRouter
from typing import List
from ..config import DEFAULT_DEVICE_ID
from ..schemas import SensorIn, EventIn, CommandOut
from ..db import get_conn
from ..crud import get_pending_commands, mark_command_done

router = APIRouter(prefix="/api/edge", tags=["edge"])

@router.post("/sensor")
@router.post("/sensor")
def edge_sensor(data: SensorIn):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO sensor_readings (device_id, temperature, humidity, light, soil_moisture)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data.device_id,
        data.temperature,
        data.humidity,
        data.light,
        data.soil_moisture,
    ))
    conn.commit()
    conn.close()
    return {"ok": True}

@router.post("/event")
def edge_event(ev: EventIn):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO actuator_events (device_id, pump_status, servo_position, source, message, command_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ev.device_id, ev.pump_status, ev.servo_position, ev.source, ev.message, ev.command_id))
    conn.commit()
    conn.close()

    if ev.command_id is not None:
        mark_command_done(ev.command_id)

    return {"ok": True}

@router.get("/commands", response_model=List[CommandOut])
def edge_commands(device_id: str = DEFAULT_DEVICE_ID):
    return get_pending_commands(device_id)
