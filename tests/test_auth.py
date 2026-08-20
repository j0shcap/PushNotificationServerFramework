"""Tests for API key authentication on protected endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import database
from database import db_session
from main import app

WRONG_KEY_HEADERS = {"Authorization": "Bearer wrong-key"}


@pytest.fixture
def anon_client(test_engine, monkeypatch):
    """TestClient that sends no Authorization header."""
    monkeypatch.setattr(database, "engine", test_engine)

    def override_db_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[db_session] = override_db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/push/send"),
        ("GET", "/devices/all"),
        ("DELETE", "/devices"),
    ],
)
def test_protected_route_rejects_missing_credentials(anon_client, method, path):
    response = anon_client.request(method, path, json={"recipients": [], "body": "x"})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/push/send"),
        ("GET", "/devices/all"),
        ("DELETE", "/devices"),
    ],
)
def test_protected_route_rejects_wrong_key(anon_client, method, path):
    response = anon_client.request(
        method, path, headers=WRONG_KEY_HEADERS, json={"recipients": [], "body": "x"}
    )

    assert response.status_code == 401


def test_register_does_not_require_credentials(anon_client):
    response = anon_client.post("/devices/register", json={"token": "abc123"})

    assert response.status_code == 200


def test_health_does_not_require_credentials(anon_client):
    assert anon_client.get("/health").status_code == 200


def test_correct_key_is_accepted(client):
    assert client.get("/devices/all").status_code == 200


def test_startup_fails_without_api_key(test_engine, monkeypatch):
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.delenv("API_KEY")

    with pytest.raises(RuntimeError, match="API_KEY"), TestClient(app):
        pass
