# routers/schedule_router.py
from fastapi import APIRouter
from ..models.schemas import ScheduleRequest
from ..services.scheduler_service import get_schedule, update_schedule

router = APIRouter(prefix="/api", tags=["schedule"])

@router.get("/schedule")
def read_schedule():
    return get_schedule()

@router.post("/schedule")
def write_schedule(req: ScheduleRequest):
    update_schedule(
        enabled=req.enabled,
        time_hhmm=req.time_hhmm,
        duration_seconds=req.duration_seconds,
        moisture_threshold=req.moisture_threshold,
    )
    return {"ok": True, "schedule": get_schedule()}
