"""Tests for application startup behavior."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

import database
from main import app


def test_startup_creates_database_tables(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(database, "engine", engine)

    with TestClient(app):
        assert "devices" in inspect(engine).get_table_names()

    engine.dispose()
