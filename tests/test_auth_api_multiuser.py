# -*- coding: utf-8 -*-
"""Tests for multi-user auth API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)

    # Reset all singletons so each test gets a completely fresh state
    from src.config import Config
    Config.reset_instance()

    from src.storage import DatabaseManager
    DatabaseManager._instance = None

    import src.auth as _auth_mod
    _auth_mod._session_secret = None
    _auth_mod._auth_enabled = None

    from api.app import create_app
    app = create_app()
    return TestClient(app)


def test_status_before_any_users(client):
    resp = client.get("/api/v1/auth/status")
    data = resp.json()
    assert data["hasUsers"] is False
    assert data["loggedIn"] is False
    assert data["user"] is None


def test_register_success(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "user@test.com",
        "password": "secret123",
        "passwordConfirm": "secret123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "user@test.com"
    assert data["nickname"] == "user"
    assert "dsa_session" in resp.cookies


def test_register_password_mismatch(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "user@test.com",
        "password": "secret123",
        "passwordConfirm": "different",
    })
    assert resp.status_code == 400


def test_status_after_register(client):
    client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "secret123", "passwordConfirm": "secret123",
    })
    resp = client.get("/api/v1/auth/status")
    data = resp.json()
    assert data["hasUsers"] is True
    assert data["loggedIn"] is True
    assert data["user"]["email"] == "user@test.com"


def test_login_success(client):
    client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "secret123", "passwordConfirm": "secret123",
    })
    client.post("/api/v1/auth/logout")
    resp = client.post("/api/v1/auth/login", json={
        "email": "user@test.com", "password": "secret123",
    })
    assert resp.status_code == 200
    assert "dsa_session" in resp.cookies


def test_login_wrong_password(client):
    client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "correct1", "passwordConfirm": "correct1",
    })
    client.post("/api/v1/auth/logout")
    resp = client.post("/api/v1/auth/login", json={
        "email": "user@test.com", "password": "wrong",
    })
    assert resp.status_code == 401


def test_register_duplicate_email(client):
    client.post("/api/v1/auth/register", json={
        "email": "dup@test.com", "password": "pass1234", "passwordConfirm": "pass1234",
    })
    resp = client.post("/api/v1/auth/register", json={
        "email": "dup@test.com", "password": "pass5678", "passwordConfirm": "pass5678",
    })
    assert resp.status_code == 400


def test_change_password(client):
    client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "oldpass1", "passwordConfirm": "oldpass1",
    })
    resp = client.post("/api/v1/auth/change-password", json={
        "currentPassword": "oldpass1",
        "newPassword": "newpass1",
        "newPasswordConfirm": "newpass1",
    })
    assert resp.status_code == 204


def test_change_password_mismatch(client):
    client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "oldpass1", "passwordConfirm": "oldpass1",
    })
    resp = client.post("/api/v1/auth/change-password", json={
        "currentPassword": "oldpass1",
        "newPassword": "newpass1",
        "newPasswordConfirm": "different",
    })
    assert resp.status_code == 400


def test_change_password_wrong_current(client):
    client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "oldpass1", "passwordConfirm": "oldpass1",
    })
    resp = client.post("/api/v1/auth/change-password", json={
        "currentPassword": "wrongone",
        "newPassword": "newpass1",
        "newPasswordConfirm": "newpass1",
    })
    assert resp.status_code == 400


def test_logout(client):
    client.post("/api/v1/auth/register", json={
        "email": "user@test.com", "password": "secret123", "passwordConfirm": "secret123",
    })
    resp = client.post("/api/v1/auth/logout")
    assert resp.status_code == 204
    # After logout, status should show loggedIn=False
    resp = client.get("/api/v1/auth/status")
    data = resp.json()
    assert data["hasUsers"] is True
    assert data["loggedIn"] is False


def test_login_no_users(client):
    """Login should fail if no users are registered."""
    resp = client.post("/api/v1/auth/login", json={
        "email": "user@test.com", "password": "secret123",
    })
    assert resp.status_code == 401
