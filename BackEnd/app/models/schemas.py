# models/schemas.py
from pydantic import BaseModel

class PumpRequest(BaseModel):
    status: str   # "on" / "off"

class ServoRequest(BaseModel):
    position: str # "open" / "half" / "close"

class ScheduleRequest(BaseModel):
    enabled: bool
    time_hhmm: str
    duration_seconds: int
    moisture_threshold: float
