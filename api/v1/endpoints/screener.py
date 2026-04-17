"""
Screener API endpoints.

Provides:
  POST /scan — SSE streaming scan results
  GET /strategies — list available strategies
"""

import json
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.services.screener_strategies import STRATEGIES

logger = logging.getLogger(__name__)

router = APIRouter()


class ScreenerScanRequest(BaseModel):
    strategy: str = Field(..., description="Strategy ID from /strategies")


def _format_sse(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/scan")
async def scan_stocks(req: ScreenerScanRequest, http_request: Request):
    """Stream screening results via SSE."""
    from src.services.screener_service import ScreenerService
    service = ScreenerService()

    async def event_generator():
        try:
            async for event in service.scan(req.strategy):
                yield _format_sse(event["type"], event.get("data", {}))
        except Exception as e:
            logger.error(f"Screener scan error: {e}", exc_info=True)
            yield _format_sse("error", {"message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/strategies")
async def list_strategies():
    """Return available screening strategies."""
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "icon": s.icon,
        }
        for s in STRATEGIES.values()
    ]
