# -*- coding: utf-8 -*-
"""Onboarding wizard endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.storage import DatabaseManager, User, UserWatchlist, AnalysisHistory

router = APIRouter()


def _get_onboarding_status(user_id: str) -> dict:
    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return {"completed": False, "steps": {}}

        settings = {}
        if user.settings:
            try:
                settings = json.loads(user.settings)
            except (json.JSONDecodeError, TypeError):
                pass

        llm_keys = [
            "GEMINI_API_KEY", "OPENAI_API_KEY", "AIHUBMIX_KEY",
            "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
        ]
        has_llm_key = any(settings.get(k, "").strip() for k in llm_keys)

        has_watchlist = session.query(UserWatchlist.id).filter_by(
            user_id=user_id
        ).first() is not None

        has_analysis = session.query(AnalysisHistory.id).filter_by(
            user_id=user_id
        ).first() is not None

        return {
            "completed": user.onboarding_completed,
            "steps": {
                "llmConfigured": has_llm_key,
                "stocksAdded": has_watchlist,
                "firstAnalysisDone": has_analysis,
            },
        }


@router.get("/status")
def get_onboarding_status(request: Request):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return {"completed": True, "steps": {}}
    return _get_onboarding_status(user_id)


@router.post("/complete")
def complete_onboarding(request: Request):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.onboarding_completed = True
            session.commit()
    return {"ok": True}
