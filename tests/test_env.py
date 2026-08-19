"""Tests for the environment variable helper."""

import pytest

from utils import getenv


def test_getenv_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("SOME_TEST_VAR", "value")

    assert getenv("SOME_TEST_VAR") == "value"


def test_getenv_raises_when_missing_and_no_default(monkeypatch):
    monkeypatch.delenv("SOME_TEST_VAR", raising=False)

    with pytest.raises(NameError):
        getenv("SOME_TEST_VAR")


def test_getenv_honors_falsy_default(monkeypatch):
    monkeypatch.delenv("SOME_TEST_VAR", raising=False)

    assert getenv("SOME_TEST_VAR", "") == ""
