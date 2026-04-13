# -*- coding: utf-8 -*-
"""
Auth middleware: protect /api/v1/* when users exist in the system.
When no users have registered yet, all endpoints are open.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.auth import COOKIE_NAME, verify_session_user

logger = logging.getLogger(__name__)

EXEMPT_PATHS = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/status",
    "/api/v1/auth/logout",
    "/api/health",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
})

EXEMPT_PREFIXES = (
    "/api/v1/share/",  # public share links
)


def _path_exempt(path: str) -> bool:
    normalized = path.rstrip("/") or "/"
    if normalized in EXEMPT_PATHS:
        return True
    for prefix in EXEMPT_PREFIXES:
        if normalized.startswith(prefix):
            return True
    return False


def has_users() -> bool:
    """Check if any users are registered. Lazy import to avoid circular deps."""
    from src.storage import DatabaseManager, User
    try:
        db = DatabaseManager.get_instance()
        with db.get_session() as session:
            return session.query(User.id).first() is not None
    except Exception:
        return False


class AuthMiddleware(BaseHTTPMiddleware):
    """Require valid user session for /api/v1/* when users exist."""

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path

        if not path.startswith("/api/v1/"):
            return await call_next(request)

        if _path_exempt(path):
            return await call_next(request)

        if not has_users():
            return await call_next(request)

        cookie_val = request.cookies.get(COOKIE_NAME)
        user_id = verify_session_user(cookie_val) if cookie_val else None
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": "Login required"},
            )

        request.state.user_id = user_id
        return await call_next(request)


def add_auth_middleware(app):
    app.add_middleware(AuthMiddleware)
