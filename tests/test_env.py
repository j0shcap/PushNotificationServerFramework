"""Tests for the environment variable helper."""

import pytest

from utils import getenv, getenv_bool


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


@pytest.mark.parametrize("value", ["1", "true", "YES ", " on"])
def test_getenv_bool_parses_truthy_values(monkeypatch, value):
    monkeypatch.setenv("SOME_TEST_VAR", value)

    assert getenv_bool("SOME_TEST_VAR") is True


@pytest.mark.parametrize("value", ["0", "false", "NO", "off", ""])
def test_getenv_bool_parses_falsy_values(monkeypatch, value):
    monkeypatch.setenv("SOME_TEST_VAR", value)

    assert getenv_bool("SOME_TEST_VAR") is False


def test_getenv_bool_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv("SOME_TEST_VAR", raising=False)

    assert getenv_bool("SOME_TEST_VAR") is False
    assert getenv_bool("SOME_TEST_VAR", default=True) is True


def test_getenv_bool_rejects_unrecognized_values(monkeypatch):
    monkeypatch.setenv("SOME_TEST_VAR", "banana")

    with pytest.raises(ValueError):
        getenv_bool("SOME_TEST_VAR")
