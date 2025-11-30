# routers/control_router.py
from fastapi import APIRouter, HTTPException
from ..models.schemas import PumpRequest, ServoRequest
from ..services.gpio_service import set_pump, set_servo_position, get_actuator_status

router = APIRouter(prefix="/api", tags=["control"])

@router.post("/pump")
def control_pump(req: PumpRequest):
    if req.status not in ["on", "off"]:
        raise HTTPException(status_code=400, detail="status must be 'on' or 'off'")
    set_pump(req.status, source="user")
    pump_status, _ = get_actuator_status()
    return {"ok": True, "pump_status": pump_status}

@router.post("/servo")
def control_servo(req: ServoRequest):
    if req.position not in ["open", "half", "close"]:
        raise HTTPException(status_code=400, detail="position must be 'open', 'half', or 'close'")
    set_servo_position(req.position, source="user")
    _, servo_pos = get_actuator_status()
    return {"ok": True, "servo_position": servo_pos}
