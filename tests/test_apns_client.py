"""Tests for the vendored APNs client, with the HTTP layer mocked."""

from pathlib import Path

import httpx
import pytest

from push.apn_handler import APNsClient, Payload, TokenCredentials
from push.apn_handler.errors import APNsException, BadDeviceToken, Unregistered

KEY_PATH = str(Path(__file__).parent / "fixtures" / "apns_test_key.p8")


def make_client(monkeypatch, status_code, json_body, requests=None):
    """Build an APNsClient whose HTTP layer returns a canned response."""

    def handler(request):
        if requests is not None:
            requests.append(request)
        return httpx.Response(status_code, json=json_body)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=transport))

    credentials = TokenCredentials(
        auth_key_path=KEY_PATH, auth_key_id="TESTKEY123", team_id="TESTTEAM12"
    )
    return APNsClient(credentials=credentials)


def test_send_notification_succeeds_on_200(monkeypatch):
    requests = []
    client = make_client(monkeypatch, 200, {}, requests)

    client.send_notification("device-token", Payload(alert="hello"), topic="com.example.test")

    request = requests[0]
    assert request.url.path == "/3/device/device-token"
    assert request.headers["apns-topic"] == "com.example.test"
    assert request.headers["authorization"].startswith("bearer ")


def test_send_notification_raises_typed_exception_for_apns_reason(monkeypatch):
    client = make_client(monkeypatch, 400, {"reason": "BadDeviceToken"})

    with pytest.raises(BadDeviceToken):
        client.send_notification("bad-token", Payload(alert="hello"), topic="com.example.test")


def test_send_notification_raises_unregistered_for_gone_token(monkeypatch):
    client = make_client(monkeypatch, 410, {"reason": "Unregistered", "timestamp": "1700000000"})

    with pytest.raises(Unregistered):
        client.send_notification("stale-token", Payload(alert="hello"), topic="com.example.test")


def test_send_notification_raises_base_exception_for_unknown_reason(monkeypatch):
    client = make_client(monkeypatch, 400, {"reason": "SomeFutureReason"})

    with pytest.raises(APNsException):
        client.send_notification("device-token", Payload(alert="hello"), topic="com.example.test")


def test_http_client_is_reused_across_sends(monkeypatch):
    constructions = []
    real_client = httpx.Client
    transport = httpx.MockTransport(lambda request: httpx.Response(200))

    def counting_client(**kwargs):
        constructions.append(kwargs)
        return real_client(transport=transport)

    monkeypatch.setattr(httpx, "Client", counting_client)
    credentials = TokenCredentials(
        auth_key_path=KEY_PATH, auth_key_id="TESTKEY123", team_id="TESTTEAM12"
    )
    client = APNsClient(credentials=credentials)

    client.send_notification("token-1", Payload(alert="a"), topic="com.example.test")
    client.send_notification("token-2", Payload(alert="b"), topic="com.example.test")

    assert len(constructions) == 1
