# -*- coding: utf-8 -*-
"""Integration tests for auth API endpoints and middleware (multi-user model).

The legacy single-admin tests (settings toggle, file-based passwords, setupState)
have been replaced. Integration tests for register/login/status/change-password
live in test_auth_api_multiuser.py. This file focuses on middleware behavior.
"""

import asyncio
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.responses import Response
from starlette.requests import Request

# Keep this test runnable when optional LLM runtime deps are not installed.
try:
    import litellm  # noqa: F401
except ModuleNotFoundError:
    sys.modules["litellm"] = MagicMock()

from api.middlewares.auth import AuthMiddleware


class AuthMiddlewareTestCase(unittest.TestCase):
    """Tests for AuthMiddleware behaviour in the multi-user model."""

    def test_protected_api_returns_401_without_session(self) -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/system/config",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "root_path": "",
        }
        request = Request(scope)
        middleware = AuthMiddleware(app=MagicMock())

        with patch("api.middlewares.auth.has_users", return_value=True):
            response = asyncio.run(middleware.dispatch(request, AsyncMock(return_value=Response(status_code=200))))

        self.assertEqual(response.status_code, 401)

    def test_protected_api_accessible_with_session(self) -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/system/config",
            "headers": [(b"cookie", b"dsa_session=test-session")],
            "query_string": b"",
            "scheme": "http",
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "root_path": "",
        }
        request = Request(scope)
        middleware = AuthMiddleware(app=MagicMock())
        next_response = Response(status_code=200)
        call_next = AsyncMock(return_value=next_response)

        with patch("api.middlewares.auth.has_users", return_value=True):
            with patch("api.middlewares.auth.verify_session_user", return_value="user123"):
                response = asyncio.run(middleware.dispatch(request, call_next))

        self.assertEqual(response.status_code, 200)
        call_next.assert_awaited_once()

    def test_no_auth_required_when_no_users(self) -> None:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/settings",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "root_path": "",
        }
        request = Request(scope)
        middleware = AuthMiddleware(app=MagicMock())
        next_response = Response(status_code=200)
        call_next = AsyncMock(return_value=next_response)

        with patch("api.middlewares.auth.has_users", return_value=False):
            response = asyncio.run(middleware.dispatch(request, call_next))

        self.assertEqual(response.status_code, 200)
        call_next.assert_awaited_once()

    def test_exempt_paths_accessible_without_session(self) -> None:
        """Verify that login, register, status, logout are exempt from auth."""
        middleware = AuthMiddleware(app=MagicMock())
        next_response = Response(status_code=200)

        for path in ["/api/v1/auth/login", "/api/v1/auth/register",
                     "/api/v1/auth/status", "/api/v1/auth/logout"]:
            scope = {
                "type": "http",
                "method": "POST",
                "path": path,
                "headers": [],
                "query_string": b"",
                "scheme": "http",
                "client": ("127.0.0.1", 1234),
                "server": ("testserver", 80),
                "root_path": "",
            }
            request = Request(scope)
            call_next = AsyncMock(return_value=next_response)

            with patch("api.middlewares.auth.has_users", return_value=True):
                response = asyncio.run(middleware.dispatch(request, call_next))

            self.assertEqual(response.status_code, 200, f"Path {path} should be exempt")
            call_next.assert_awaited_once()

    def test_change_password_requires_session(self) -> None:
        """change-password is NOT exempt — middleware should block unauthenticated requests."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/change-password",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "root_path": "",
        }
        request = Request(scope)
        middleware = AuthMiddleware(app=MagicMock())

        with patch("api.middlewares.auth.has_users", return_value=True):
            response = asyncio.run(middleware.dispatch(request, AsyncMock(return_value=Response(status_code=200))))

        self.assertEqual(response.status_code, 401)

    def test_non_api_paths_skip_middleware(self) -> None:
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/some/frontend/page",
            "headers": [],
            "query_string": b"",
            "scheme": "http",
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
            "root_path": "",
        }
        request = Request(scope)
        middleware = AuthMiddleware(app=MagicMock())
        next_response = Response(status_code=200)
        call_next = AsyncMock(return_value=next_response)

        response = asyncio.run(middleware.dispatch(request, call_next))

        self.assertEqual(response.status_code, 200)
        call_next.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
