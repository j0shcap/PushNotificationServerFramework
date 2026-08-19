"""Tests for the /push endpoints."""

from main import app
from push import get_push_handler
from push.handler import PushHandler


def override_handler(handler):
    app.dependency_overrides[get_push_handler] = lambda: handler


def test_send_push_returns_per_token_results(client, apns_handler_factory):
    override_handler(
        apns_handler_factory(
            {
                "good-token": (200, {}),
                "bad-token": (400, {"reason": "BadDeviceToken"}),
            }
        )
    )

    response = client.post(
        "/push/send",
        json={"recipients": ["good-token", "bad-token"], "body": "hello"},
    )

    assert response.status_code == 200
    assert response.json() == {"good-token": "Success", "bad-token": "BadDeviceToken"}


def test_send_push_removes_unregistered_devices(client, apns_handler_factory):
    override_handler(
        apns_handler_factory(
            {
                "good-token": (200, {}),
                "stale-token": (410, {"reason": "Unregistered", "timestamp": "1700000000"}),
            }
        )
    )
    client.post("/devices/register", json={"token": "good-token"})
    client.post("/devices/register", json={"token": "stale-token"})

    client.post(
        "/push/send",
        json={"recipients": ["good-token", "stale-token"], "body": "hello"},
    )

    remaining = {device["token"] for device in client.get("/devices/all").json()}
    assert remaining == {"good-token"}


def test_push_handler_is_shared_across_requests(monkeypatch):
    import push.handler

    monkeypatch.setattr(push.handler, "_shared_handler", None)

    first = get_push_handler()
    second = get_push_handler()

    assert isinstance(first, PushHandler)
    assert first is second
