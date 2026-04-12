"""Per-user analysis schedule endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from src.services.user_schedule_service import UserScheduleService
from src.storage import DatabaseManager

router = APIRouter()


class UpdateScheduleRequest(BaseModel):
    enabled: bool
    time: str = Field(min_length=4, max_length=5)


def _get_service() -> UserScheduleService:
    db = DatabaseManager.get_instance()
    return UserScheduleService(db._SessionLocal)


@router.get("")
def get_schedule(request: Request):
    user_id = request.state.user_id
    return _get_service().get_schedule(user_id)


@router.put("")
def update_schedule(request: Request, body: UpdateScheduleRequest):
    user_id = request.state.user_id
    try:
        return _get_service().update_schedule(user_id, body.enabled, body.time)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@router.post("/run-now")
def run_now(request: Request):
    """Manually trigger scheduled analysis for the current user."""
    user_id = request.state.user_id
    result = _get_service().run_user_analysis(user_id)
    return result
