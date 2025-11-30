# app/schemas.py
from pydantic import BaseModel
from typing import Optional, Dict, List

# Dipakai FE
class PumpRequest(BaseModel):
    status: str   # "on" / "off"

class ServoRequest(BaseModel):
    position: str # "open" / "half" / "close"

class ScheduleRequest(BaseModel):
    enabled: bool
    time_hhmm: str
    duration_seconds: int
    moisture_threshold: float

# Dipakai Edge (Raspi)
class SensorIn(BaseModel):
    device_id: str
    temperature: float
    humidity: float
    light: float
    soil_moisture: float

class EventIn(BaseModel):
    device_id: str
    pump_status: Optional[str] = None
    servo_position: Optional[str] = None
    source: str = "edge"   # "user", "auto", "edge"
    message: str = ""
    command_id: Optional[int] = None

class CommandOut(BaseModel):
    id: int
    type: str
    payload: Dict
