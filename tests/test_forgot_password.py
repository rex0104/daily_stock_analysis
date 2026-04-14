# -*- coding: utf-8 -*-
"""Tests for forgot-password / reset-password flow."""

import secrets

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    monkeypatch.setenv("ENV_FILE", str(tmp_path / "nonexistent.env"))
    # Reset singleton so each test gets a fresh DB
    from src.storage import DatabaseManager
    DatabaseManager._instance = None
    from api.app import create_app
    app = create_app()
    return TestClient(app)


def _register(client, email="user@test.com"):
    return client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "test1234",
        "passwordConfirm": "test1234",
    })


def test_forgot_password_returns_ok_for_existing_email(client):
    _register(client)
    client.post("/api/v1/auth/logout")
    resp = client.post("/api/v1/auth/forgot-password", json={"email": "user@test.com"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_forgot_password_returns_ok_for_unknown_email(client):
    """Should NOT reveal that email doesn't exist."""
    resp = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@test.com"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_reset_password_with_valid_token(client):
    _register(client)
    client.post("/api/v1/auth/logout")

    # Generate token directly (bypass email sending)
    from src.storage import DatabaseManager, PasswordResetToken, User
    db = DatabaseManager.get_instance()
    token = secrets.token_urlsafe(48)
    with db.get_session() as s:
        user = s.query(User).first()
        s.add(PasswordResetToken(user_id=user.id, token=token))
        s.commit()

    resp = client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "password": "newpass1",
        "passwordConfirm": "newpass1",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify can login with new password
    resp = client.post("/api/v1/auth/login", json={
        "email": "user@test.com",
        "password": "newpass1",
    })
    assert resp.status_code == 200


def test_reset_password_with_invalid_token(client):
    resp = client.post("/api/v1/auth/reset-password", json={
        "token": "invalid-token-value",
        "password": "newpass1",
        "passwordConfirm": "newpass1",
    })
    assert resp.status_code == 400


def test_reset_password_mismatch(client):
    resp = client.post("/api/v1/auth/reset-password", json={
        "token": "anytoken",
        "password": "newpass1",
        "passwordConfirm": "different",
    })
    assert resp.status_code == 400


def test_reset_token_single_use(client):
    _register(client)
    client.post("/api/v1/auth/logout")

    from src.storage import DatabaseManager, PasswordResetToken, User
    db = DatabaseManager.get_instance()
    token = secrets.token_urlsafe(48)
    with db.get_session() as s:
        user = s.query(User).first()
        s.add(PasswordResetToken(user_id=user.id, token=token))
        s.commit()

    # First use should succeed
    resp = client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "password": "newpass1",
        "passwordConfirm": "newpass1",
    })
    assert resp.status_code == 200

    # Second use should fail (token already used)
    resp = client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "password": "newpass2",
        "passwordConfirm": "newpass2",
    })
    assert resp.status_code == 400


def test_reset_password_expired_token(client):
    _register(client)
    client.post("/api/v1/auth/logout")

    from datetime import datetime, timedelta
    from src.storage import DatabaseManager, PasswordResetToken, User
    db = DatabaseManager.get_instance()
    token = secrets.token_urlsafe(48)
    with db.get_session() as s:
        user = s.query(User).first()
        # Create token that expired 31 minutes ago
        expired_time = datetime.now() - timedelta(minutes=31)
        s.add(PasswordResetToken(user_id=user.id, token=token, created_at=expired_time))
        s.commit()

    resp = client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "password": "newpass1",
        "passwordConfirm": "newpass1",
    })
    assert resp.status_code == 400
    assert resp.json()["error"] == "token_expired"
