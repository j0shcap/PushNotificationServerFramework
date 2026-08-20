"""Tests for the database session dependency."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool

import database


def test_db_session_yields_working_session_and_releases_connection(monkeypatch):
    engine = create_engine("sqlite://", poolclass=QueuePool)
    monkeypatch.setattr(database, "engine", engine)

    generator = database.db_session()
    session = next(generator)
    assert session.execute(text("SELECT 1")).scalar() == 1
    assert engine.pool.checkedout() == 1

    with pytest.raises(StopIteration):
        next(generator)

    assert engine.pool.checkedout() == 0
    engine.dispose()
