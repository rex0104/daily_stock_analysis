"""Watchlist (favorites) API endpoints."""
from __future__ import annotations
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from src.services.watchlist_service import WatchlistService
from src.storage import DatabaseManager

router = APIRouter()


class AddWatchlistRequest(BaseModel):
    stock_code: str = Field(..., alias="stockCode", min_length=1, max_length=10)
    stock_name: str | None = Field(None, alias="stockName")
    model_config = {"populate_by_name": True}


def _get_service() -> WatchlistService:
    db = DatabaseManager.get_instance()
    return WatchlistService(db._SessionLocal)


@router.get("")
def list_watchlist(request: Request):
    user_id = request.state.user_id
    items = _get_service().list(user_id)
    return {"items": items}


@router.post("")
def add_to_watchlist(request: Request, body: AddWatchlistRequest):
    user_id = request.state.user_id
    item = _get_service().add(user_id, body.stock_code, body.stock_name)
    return item


@router.delete("/{stock_code}")
def remove_from_watchlist(request: Request, stock_code: str):
    user_id = request.state.user_id
    removed = _get_service().remove(user_id, stock_code)
    if not removed:
        return JSONResponse(status_code=404, content={"error": "not_found"})
    return {"ok": True}
