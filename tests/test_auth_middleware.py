# tests/test_auth_middleware.py
import pytest
from unittest.mock import patch
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from api.middlewares.auth import AuthMiddleware


def _make_app():
    app = FastAPI()
    app.add_middleware(AuthMiddleware)

    @app.get("/api/v1/test")
    def test_endpoint(request: Request):
        user_id = getattr(request.state, "user_id", None)
        return {"user_id": user_id}

    @app.get("/api/v1/auth/status")
    def status_endpoint():
        return {"ok": True}

    @app.get("/api/v1/auth/register")
    def register_endpoint():
        return {"ok": True}

    @app.get("/api/v1/share/abc123")
    def share_endpoint():
        return {"ok": True}

    @app.get("/not-api")
    def non_api():
        return {"ok": True}

    return app


@patch("api.middlewares.auth.has_users", return_value=True)
@patch("api.middlewares.auth.verify_session_user", return_value="user123")
def test_valid_session_injects_user_id(mock_verify, mock_has_users):
    client = TestClient(_make_app())
    resp = client.get("/api/v1/test", cookies={"dsa_session": "fake.token.here.sig"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "user123"


@patch("api.middlewares.auth.has_users", return_value=True)
@patch("api.middlewares.auth.verify_session_user", return_value=None)
def test_invalid_session_returns_401(mock_verify, mock_has_users):
    client = TestClient(_make_app())
    resp = client.get("/api/v1/test", cookies={"dsa_session": "bad"})
    assert resp.status_code == 401


@patch("api.middlewares.auth.has_users", return_value=True)
def test_no_cookie_returns_401(mock_has_users):
    client = TestClient(_make_app())
    resp = client.get("/api/v1/test")
    assert resp.status_code == 401


@patch("api.middlewares.auth.has_users", return_value=False)
def test_no_users_allows_all(mock_has_users):
    client = TestClient(_make_app())
    resp = client.get("/api/v1/test")
    assert resp.status_code == 200


@patch("api.middlewares.auth.has_users", return_value=True)
def test_exempt_path_status(mock_has_users):
    client = TestClient(_make_app())
    resp = client.get("/api/v1/auth/status")
    assert resp.status_code == 200


@patch("api.middlewares.auth.has_users", return_value=True)
def test_exempt_path_register(mock_has_users):
    client = TestClient(_make_app())
    resp = client.get("/api/v1/auth/register")
    assert resp.status_code == 200


@patch("api.middlewares.auth.has_users", return_value=True)
def test_exempt_prefix_share(mock_has_users):
    client = TestClient(_make_app())
    resp = client.get("/api/v1/share/abc123")
    assert resp.status_code == 200


def test_non_api_path_skips_auth():
    client = TestClient(_make_app())
    resp = client.get("/not-api")
    assert resp.status_code == 200
