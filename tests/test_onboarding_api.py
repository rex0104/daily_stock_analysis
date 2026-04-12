# -*- coding: utf-8 -*-
"""Tests for onboarding API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DATABASE_PATH", db_path)
    # Point ENV_FILE to a nonexistent file so env migration doesn't
    # copy real LLM keys into the first user's settings.
    monkeypatch.setenv("ENV_FILE", str(tmp_path / "nonexistent.env"))

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


def _register(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "test@test.com", "password": "test1234", "passwordConfirm": "test1234",
    })
    assert resp.status_code == 200
    return resp


def test_onboarding_status_new_user(client):
    _register(client)
    resp = client.get("/api/v1/onboarding/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed"] is False
    assert data["steps"]["llmConfigured"] is False
    assert data["steps"]["stocksAdded"] is False
    assert data["steps"]["firstAnalysisDone"] is False


def test_onboarding_complete(client):
    _register(client)
    resp = client.post("/api/v1/onboarding/complete")
    assert resp.status_code == 200
    # Check status now shows completed
    resp = client.get("/api/v1/onboarding/status")
    assert resp.json()["completed"] is True


def test_auth_status_includes_onboarding(client):
    _register(client)
    resp = client.get("/api/v1/auth/status")
    data = resp.json()
    assert "onboardingCompleted" in data
    assert data["onboardingCompleted"] is False
