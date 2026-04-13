# -*- coding: utf-8 -*-
"""Unit tests for Auth /status contract (multi-user model).

Replaces the legacy setupState / settings tests — those endpoints and
response fields were removed in the multi-user rewrite.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from starlette.requests import Request

import src.auth as auth


def _reset_auth_globals() -> None:
    """Reset auth module globals for test isolation."""
    auth._auth_enabled = None
    auth._session_secret = None
    auth._rate_limit = {}


def _make_request(*, cookies: dict[str, str] | None = None) -> Request:
    """Create a minimal Starlette request for endpoint unit tests."""
    headers: list[tuple[bytes, bytes]] = []
    if cookies:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        headers.append((b"cookie", cookie_header.encode("utf-8")))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/auth/status",
        "raw_path": b"/api/v1/auth/status",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


class TestAuthStatusNewContract:
    """Verify the new /status endpoint returns hasUsers, loggedIn, user."""

    def setup_method(self):
        _reset_auth_globals()

    def teardown_method(self):
        _reset_auth_globals()

    def test_status_no_users(self):
        """When no users exist, hasUsers=False, loggedIn=False, user=None."""
        from api.v1.endpoints.auth import auth_status

        mock_svc = MagicMock()
        mock_svc.has_users.return_value = False

        request = _make_request()
        with patch("api.v1.endpoints.auth._get_user_service", return_value=mock_svc):
            data = asyncio.run(auth_status(request))

        assert data["hasUsers"] is False
        assert data["loggedIn"] is False
        assert data["user"] is None

    def test_status_has_users_not_logged_in(self):
        """When users exist but no valid session, loggedIn=False."""
        from api.v1.endpoints.auth import auth_status

        mock_svc = MagicMock()
        mock_svc.has_users.return_value = True

        request = _make_request()
        with patch("api.v1.endpoints.auth._get_user_service", return_value=mock_svc):
            data = asyncio.run(auth_status(request))

        assert data["hasUsers"] is True
        assert data["loggedIn"] is False
        assert data["user"] is None

    def test_status_has_users_logged_in(self):
        """When users exist and session is valid, loggedIn=True with user info."""
        from api.v1.endpoints.auth import auth_status

        user_info = {"id": "abc123", "email": "test@test.com", "nickname": "test"}
        mock_svc = MagicMock()
        mock_svc.has_users.return_value = True
        mock_svc.get_user.return_value = user_info

        request = _make_request(cookies={"dsa_session": "fake.token.here.sig"})
        with patch("api.v1.endpoints.auth._get_user_service", return_value=mock_svc):
            with patch("api.v1.endpoints.auth.verify_session_user", return_value="abc123"):
                data = asyncio.run(auth_status(request))

        assert data["hasUsers"] is True
        assert data["loggedIn"] is True
        assert data["user"] == user_info
