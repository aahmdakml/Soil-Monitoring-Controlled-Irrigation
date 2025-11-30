# routers/status_router.py
from fastapi import APIRouter
from ..services.sensor_service import get_latest_sensor, get_history
from ..services.event_service import get_logs
from ..services.gpio_service import get_actuator_status
from ..services.scheduler_service import get_schedule

router = APIRouter(prefix="/api", tags=["status"])

@router.get("/status")
def read_status():
    sensor = get_latest_sensor()
    pump_status, servo_pos = get_actuator_status()
    sched = get_schedule()
    return {
        "sensor": sensor,
        "pump_status": pump_status,
        "servo_position": servo_pos,
        "schedule": sched,
    }

@router.get("/history")
def read_history(limit: int = 50):
    return get_history(limit)

@router.get("/logs")
def read_logs(limit: int = 50):
    return get_logs(limit)
