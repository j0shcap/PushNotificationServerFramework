"""Shared test fixtures.

Environment variables are set before any application import because
database.py builds its engine and utils/env.py reads the environment at
import time. The APNs key is a throwaway EC P-256 key generated for tests
only; it has never been registered with Apple.
"""

import os
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("APNS_KEY_ID", "TESTKEY123")
os.environ.setdefault("APNS_TEAM_ID", "TESTTEAM12")
os.environ.setdefault("APNS_APP_BUNDLE_ID", "com.example.test")
os.environ.setdefault("APNS_AUTH_KEY_PATH", str(FIXTURES_DIR / "apns_test_key.p8"))
os.environ.setdefault("API_KEY", "test-api-key")

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import database
from database import db_session
from entities import EntityBase
from main import app
from push import PushHandler


@pytest.fixture
def test_engine():
    """In-memory SQLite engine with the application schema created."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    EntityBase.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def client(test_engine, monkeypatch):
    """Authenticated TestClient wired to the in-memory database."""
    monkeypatch.setattr(database, "engine", test_engine)

    def override_db_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[db_session] = override_db_session
    headers = {"Authorization": f"Bearer {os.environ['API_KEY']}"}
    with TestClient(app, headers=headers) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def apns_handler_factory(monkeypatch):
    """Build PushHandlers whose APNs response depends on the device token."""

    def factory(responses_by_token):
        def route(request):
            token = request.url.path.rsplit("/", 1)[-1]
            status_code, body = responses_by_token[token]
            return httpx.Response(status_code, json=body)

        transport = httpx.MockTransport(route)
        real_client = httpx.Client
        monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=transport))
        return PushHandler()

    return factory
