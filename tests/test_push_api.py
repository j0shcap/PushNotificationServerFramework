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
                "stale-token-2": (410, {"reason": "Unregistered", "timestamp": "1700000000"}),
            }
        )
    )
    client.post("/devices/register", json={"token": "good-token"})
    client.post("/devices/register", json={"token": "stale-token"})
    client.post("/devices/register", json={"token": "stale-token-2"})

    client.post(
        "/push/send",
        json={"recipients": ["good-token", "stale-token", "stale-token-2"], "body": "hello"},
    )

    remaining = {device["token"] for device in client.get("/devices/all").json()}
    assert remaining == {"good-token"}


def test_push_handler_is_shared_across_requests(monkeypatch):
    import httpx

    import push.handler

    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=transport))
    monkeypatch.setattr(push.handler, "_shared_handler", None)

    first = get_push_handler()
    second = get_push_handler()

    assert isinstance(first, PushHandler)
    assert first is second


def test_shutdown_closes_shared_push_handler(monkeypatch, test_engine):
    import httpx
    from fastapi.testclient import TestClient

    import database
    import push.handler

    clients = []
    real_client = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200))

    def tracking_client(**kwargs):
        http_client = real_client(transport=transport)
        clients.append(http_client)
        return http_client

    monkeypatch.setattr(httpx, "Client", tracking_client)
    monkeypatch.setattr(push.handler, "_shared_handler", None)
    monkeypatch.setattr(database, "engine", test_engine)

    with TestClient(app):
        get_push_handler()

    assert clients and all(client.is_closed for client in clients)
    assert push.handler._shared_handler is None


def test_send_push_with_no_recipients_returns_empty_results(client, apns_handler_factory):
    override_handler(apns_handler_factory({}))

    response = client.post("/push/send", json={"recipients": [], "body": "hello"})

    assert response.status_code == 200
    assert response.json() == {}


def test_prune_failure_does_not_discard_push_results(client, apns_handler_factory):
    from sqlalchemy.exc import OperationalError

    from services import DeviceService

    override_handler(
        apns_handler_factory(
            {
                "good-token": (200, {}),
                "stale-token": (410, {"reason": "Unregistered", "timestamp": "1700000000"}),
            }
        )
    )

    class FailingDeviceService(DeviceService):
        def remove_devices(self, tokens):
            raise OperationalError("DELETE", {}, Exception("db gone"))

    app.dependency_overrides[DeviceService] = FailingDeviceService

    response = client.post(
        "/push/send",
        json={"recipients": ["good-token", "stale-token"], "body": "hello"},
    )

    assert response.status_code == 200
    assert response.json() == {"good-token": "Success", "stale-token": "Unregistered"}
