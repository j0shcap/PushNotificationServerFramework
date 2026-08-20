"""Tests for API key authentication on protected endpoints."""

import pytest
from fastapi.testclient import TestClient

import database
from main import app

WRONG_KEY_HEADERS = {"Authorization": "Bearer wrong-key"}


def test_protected_route_rejects_missing_credentials(anon_client, protected_route):
    method, path = protected_route

    response = anon_client.request(method, path, json={"recipients": [], "body": "x"})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_protected_route_rejects_wrong_key(anon_client, protected_route):
    method, path = protected_route

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


def test_missing_api_key_at_request_time_yields_401_not_500(anon_client, monkeypatch):
    monkeypatch.delenv("API_KEY")

    response = anon_client.get("/devices/all", headers={"Authorization": "Bearer anything"})

    assert response.status_code == 401


def test_placeholder_api_key_logs_a_warning(test_engine, monkeypatch, caplog):
    monkeypatch.setattr(database, "engine", test_engine)
    monkeypatch.setenv("API_KEY", "CHANGE_ME")

    with TestClient(app):
        pass

    assert any("CHANGE_ME" in record.message for record in caplog.records)
