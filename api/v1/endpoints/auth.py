# -*- coding: utf-8 -*-
"""Authentication endpoints for multi-user login."""

from __future__ import annotations

import logging
import os
import secrets
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from src.auth import (
    COOKIE_NAME,
    SESSION_MAX_AGE_HOURS_DEFAULT,
    check_rate_limit,
    clear_rate_limit,
    create_user_session,
    get_client_ip,
    record_login_failure,
    verify_session_user,
)
from src.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    """Register a new user account."""

    model_config = {"populate_by_name": True}

    email: str
    password: str
    password_confirm: str = Field(alias="passwordConfirm")


class LoginRequest(BaseModel):
    """Login with email and password."""

    model_config = {"populate_by_name": True}

    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    """Change password request body."""

    model_config = {"populate_by_name": True}

    current_password: str = Field(default="", alias="currentPassword")
    new_password: str = Field(default="", alias="newPassword")
    new_password_confirm: str = Field(default="", alias="newPasswordConfirm")


class ForgotPasswordRequest(BaseModel):
    """Request a password reset email."""

    email: str


class ResetPasswordRequest(BaseModel):
    """Reset password using a valid token."""

    model_config = {"populate_by_name": True}

    token: str
    password: str = Field(min_length=6)
    password_confirm: str = Field(alias="passwordConfirm")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_service() -> UserService:
    """Instantiate UserService backed by the app database."""
    from src.storage import DatabaseManager
    db = DatabaseManager.get_instance()
    return UserService(db._SessionLocal)


def _cookie_params(request: Request) -> dict:
    """Build cookie params including Secure based on request."""
    secure = False
    if os.getenv("TRUST_X_FORWARDED_FOR", "false").lower() == "true":
        proto = request.headers.get("X-Forwarded-Proto", "").lower()
        secure = proto == "https"
    else:
        secure = request.url.scheme == "https"

    try:
        max_age_hours = int(os.getenv("ADMIN_SESSION_MAX_AGE_HOURS", str(SESSION_MAX_AGE_HOURS_DEFAULT)))
    except ValueError:
        max_age_hours = SESSION_MAX_AGE_HOURS_DEFAULT
    max_age = max_age_hours * 3600

    return {
        "httponly": True,
        "samesite": "lax",
        "secure": secure,
        "path": "/",
        "max_age": max_age,
    }


def _set_session_cookie(response: Response, session_value: str, request: Request) -> None:
    """Attach the session cookie to a response."""
    params = _cookie_params(request)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_value,
        httponly=params["httponly"],
        samesite=params["samesite"],
        secure=params["secure"],
        path=params["path"],
        max_age=params["max_age"],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    summary="Register a new user",
    description="Create a new user account with email and password.",
)
async def auth_register(request: Request, body: RegisterRequest):
    """Register a new user. First user automatically claims orphan data."""
    password = (body.password or "").strip()
    confirm = (body.password_confirm or "").strip()

    if not password:
        return JSONResponse(
            status_code=400,
            content={"error": "password_required", "message": "Password is required"},
        )

    if password != confirm:
        return JSONResponse(
            status_code=400,
            content={"error": "password_mismatch", "message": "Passwords do not match"},
        )

    svc = _get_user_service()
    was_first = not svc.has_users()

    try:
        user = svc.register(body.email, password)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": "registration_failed", "message": str(exc)},
        )

    # First user claims pre-existing (orphan) data
    if was_first:
        try:
            from src.services.data_claim_service import claim_orphan_data
            from src.storage import DatabaseManager
            db = DatabaseManager.get_instance()
            claim_orphan_data(db._SessionLocal, user["id"])
        except ImportError:
            logger.debug("data_claim_service not available, skipping orphan data claim")
        except Exception as exc:
            logger.warning("Failed to claim orphan data for first user: %s", exc)

    session_val = create_user_session(user["id"])
    if not session_val:
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "Failed to create session"},
        )

    resp = JSONResponse(content={
        "id": user["id"],
        "email": user["email"],
        "nickname": user["nickname"],
    })
    _set_session_cookie(resp, session_val, request)
    return resp


@router.post(
    "/login",
    summary="Login with email and password",
    description="Verify credentials and set session cookie.",
)
async def auth_login(request: Request, body: LoginRequest):
    """Authenticate user by email + password, set cookie on success."""
    email = (body.email or "").strip()
    password = (body.password or "").strip()

    if not email or not password:
        return JSONResponse(
            status_code=400,
            content={"error": "credentials_required", "message": "Email and password are required"},
        )

    ip = get_client_ip(request)
    if not check_rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limited",
                "message": "Too many failed attempts. Please try again later.",
            },
        )

    svc = _get_user_service()
    user = svc.login(email, password)
    if user is None:
        record_login_failure(ip)
        return JSONResponse(
            status_code=401,
            content={"error": "invalid_credentials", "message": "Invalid email or password"},
        )

    clear_rate_limit(ip)
    session_val = create_user_session(user["id"])
    if not session_val:
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "message": "Failed to create session"},
        )

    resp = JSONResponse(content={
        "id": user["id"],
        "email": user["email"],
        "nickname": user["nickname"],
    })
    _set_session_cookie(resp, session_val, request)
    return resp


@router.get(
    "/status",
    summary="Get auth status",
    description="Returns whether users exist, current login state, and user info.",
)
async def auth_status(request: Request):
    """Return hasUsers, loggedIn, user — no auth required."""
    svc = _get_user_service()
    has_users = svc.has_users()

    logged_in = False
    user_info = None
    onboarding_completed = False

    if has_users:
        cookie_val = request.cookies.get(COOKIE_NAME)
        if cookie_val:
            user_id = verify_session_user(cookie_val)
            if user_id:
                user_info = svc.get_user(user_id)
                logged_in = user_info is not None
                if logged_in:
                    try:
                        from src.storage import DatabaseManager, User as UserModel
                        db = DatabaseManager.get_instance()
                        with db.get_session() as session:
                            user_row = session.query(UserModel).filter_by(id=user_id).first()
                            onboarding_completed = bool(user_row.onboarding_completed) if user_row else False
                    except Exception:
                        pass

    return {
        "hasUsers": has_users,
        "loggedIn": logged_in,
        "user": user_info,
        "onboardingCompleted": onboarding_completed,
    }


@router.post(
    "/change-password",
    summary="Change password",
    description="Change password for the currently logged-in user.",
)
async def auth_change_password(request: Request, body: ChangePasswordRequest):
    """Change password. Requires a valid session (middleware sets request.state.user_id)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return JSONResponse(
            status_code=401,
            content={"error": "unauthorized", "message": "Login required"},
        )

    current = (body.current_password or "").strip()
    new_pwd = (body.new_password or "").strip()
    new_confirm = (body.new_password_confirm or "").strip()

    if not current:
        return JSONResponse(
            status_code=400,
            content={"error": "current_required", "message": "Current password is required"},
        )
    if new_pwd != new_confirm:
        return JSONResponse(
            status_code=400,
            content={"error": "password_mismatch", "message": "New passwords do not match"},
        )

    svc = _get_user_service()
    try:
        svc.change_password(user_id, current, new_pwd)
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_password", "message": str(exc)},
        )

    return Response(status_code=204)


@router.post(
    "/logout",
    summary="Logout",
    description="Clear session cookie.",
)
async def auth_logout(request: Request):
    """Clear session cookie."""
    resp = Response(status_code=204)
    resp.delete_cookie(key=COOKIE_NAME, path="/")
    return resp


# ---------------------------------------------------------------------------
# Password reset helpers
# ---------------------------------------------------------------------------

_RESET_TOKEN_EXPIRY_MINUTES = 30


def _get_reset_origin(request: Request) -> str:
    """Derive the frontend origin for the reset link."""
    # Prefer explicit env config
    base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    if base:
        return base
    # Fall back to Origin / Referer header
    origin = request.headers.get("origin", "").strip().rstrip("/")
    if origin:
        return origin
    referer = request.headers.get("referer", "").strip()
    if referer:
        from urllib.parse import urlparse
        parsed = urlparse(referer)
        return f"{parsed.scheme}://{parsed.netloc}"
    # Last resort
    scheme = request.url.scheme
    if os.getenv("TRUST_X_FORWARDED_FOR", "false").lower() == "true":
        proto = request.headers.get("X-Forwarded-Proto", "").lower()
        if proto:
            scheme = proto
    return f"{scheme}://{request.url.netloc}"


def _send_reset_email(to_email: str, reset_url: str) -> bool:
    """Send password reset email using platform SMTP config."""
    sender = os.getenv("EMAIL_SENDER", "").strip()
    password = os.getenv("EMAIL_PASSWORD", "").strip()
    smtp_host = os.getenv("EMAIL_SMTP_HOST", "smtp.qq.com").strip()
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "465"))

    if not sender or not password:
        logger.warning("Email not configured, cannot send reset email")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "密码重置 - DSA"
    msg["From"] = sender
    msg["To"] = to_email

    html = f"""\
<div style="max-width:480px;margin:0 auto;font-family:system-ui,sans-serif;color:#333">
    <h2>密码重置</h2>
    <p>您请求了密码重置，点击下方按钮设置新密码：</p>
    <p style="text-align:center;margin:24px 0">
        <a href="{reset_url}"
           style="display:inline-block;padding:12px 32px;background:#0891b2;color:#fff;
                  text-decoration:none;border-radius:8px;font-weight:600">
            重置密码
        </a>
    </p>
    <p style="font-size:13px;color:#888">
        链接有效期 {_RESET_TOKEN_EXPIRY_MINUTES} 分钟。如果您没有请求密码重置，请忽略此邮件。
    </p>
</div>"""
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        return True
    except Exception as exc:
        logger.error("Failed to send reset email: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Forgot / Reset password endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/forgot-password",
    summary="Request password reset",
    description="Send a password reset link to the given email. Always returns 200.",
)
async def auth_forgot_password(request: Request, body: ForgotPasswordRequest):
    """Send password reset email. Always returns 200 to avoid leaking email existence."""
    email = (body.email or "").strip().lower()
    if not email:
        return {"ok": True}

    from src.storage import DatabaseManager, User, PasswordResetToken

    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        user = session.query(User).filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(48)
            session.add(PasswordResetToken(
                user_id=user.id,
                token=token,
                created_at=datetime.now(),
            ))
            session.commit()

            origin = _get_reset_origin(request)
            reset_url = f"{origin}/reset-password?token={token}"
            _send_reset_email(email, reset_url)

    return {"ok": True}


@router.post(
    "/reset-password",
    summary="Reset password with token",
    description="Reset the user's password using a valid reset token.",
)
async def auth_reset_password(body: ResetPasswordRequest):
    """Reset password using a valid, unexpired token."""
    password = (body.password or "").strip()
    confirm = (body.password_confirm or "").strip()

    if not password or len(password) < 6:
        return JSONResponse(
            status_code=400,
            content={"error": "password_too_short", "message": "Password must be at least 6 characters"},
        )

    if password != confirm:
        return JSONResponse(
            status_code=400,
            content={"error": "password_mismatch", "message": "Passwords do not match"},
        )

    from src.storage import DatabaseManager, PasswordResetToken

    db = DatabaseManager.get_instance()
    with db.get_session() as session:
        record = session.query(PasswordResetToken).filter_by(
            token=body.token, used=False,
        ).first()

        if not record:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_token", "message": "Invalid or expired reset token"},
            )

        elapsed = datetime.now() - record.created_at
        if elapsed > timedelta(minutes=_RESET_TOKEN_EXPIRY_MINUTES):
            return JSONResponse(
                status_code=400,
                content={"error": "token_expired", "message": "Reset token has expired"},
            )

        # Update password via UserService (handles hashing)
        svc = _get_user_service()
        try:
            svc.reset_password(record.user_id, password)
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={"error": "reset_failed", "message": str(exc)},
            )

        record.used = True
        session.commit()

    return {"ok": True}
