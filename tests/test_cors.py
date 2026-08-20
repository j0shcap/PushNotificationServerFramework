"""Tests for CORS configuration."""

from fastapi.testclient import TestClient

from main import create_app

PREFLIGHT_HEADERS = {
    "Origin": "https://example.com",
    "Access-Control-Request-Method": "POST",
}


def test_no_cors_headers_by_default(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    client = TestClient(create_app())

    response = client.options("/devices/register", headers=PREFLIGHT_HEADERS)

    assert "access-control-allow-origin" not in response.headers


def test_configured_origin_is_allowed(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://example.com, https://other.example")
    client = TestClient(create_app())

    response = client.options("/devices/register", headers=PREFLIGHT_HEADERS)

    assert response.headers["access-control-allow-origin"] == "https://example.com"


def test_unlisted_origin_is_rejected(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
    client = TestClient(create_app())

    response = client.options(
        "/devices/register",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )

    assert "access-control-allow-origin" not in response.headers
