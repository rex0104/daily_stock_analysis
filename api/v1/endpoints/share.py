"""Public report sharing API endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from src.services.share_service import ShareService
from src.storage import DatabaseManager

router = APIRouter()


class CreateShareRequest(BaseModel):
    analysis_history_id: int = Field(..., alias="analysisHistoryId")
    brand_name: str | None = Field(None, alias="brandName")
    model_config = {"populate_by_name": True}


def _get_service() -> ShareService:
    db = DatabaseManager.get_instance()
    return ShareService(db._SessionLocal)


@router.post("")
def create_share(request: Request, body: CreateShareRequest):
    user_id = request.state.user_id
    try:
        result = _get_service().create(user_id, body.analysis_history_id, body.brand_name)
        return result
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})


@router.get("")
def list_my_shares(request: Request):
    user_id = request.state.user_id
    shares = _get_service().list_by_user(user_id)
    return {"items": shares}


@router.get("/{token}")
def get_shared_report(token: str):
    """Public endpoint — no auth required."""
    report = _get_service().get_by_token(token)
    if not report:
        return JSONResponse(status_code=404, content={"error": "Share link not found or revoked"})
    return report


@router.delete("/{token}")
def revoke_share(request: Request, token: str):
    user_id = request.state.user_id
    if not _get_service().revoke(user_id, token):
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return {"ok": True}
