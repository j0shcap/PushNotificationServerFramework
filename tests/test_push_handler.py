"""Tests for PushHandler, with the HTTP layer mocked per device token."""

import httpx
import pytest

from push import PushHandler


def test_send_multiple_push_returns_result_per_token(apns_handler_factory):
    handler = apns_handler_factory(
        {
            "good-token": (200, {}),
            "stale-token": (410, {"reason": "Unregistered", "timestamp": "1700000000"}),
            "other-token": (200, {}),
        }
    )

    results = handler.send_multiple_push(
        to_device_tokens=["good-token", "stale-token", "other-token"], body="hello"
    )

    assert results == {
        "good-token": "Success",
        "stale-token": "Unregistered",
        "other-token": "Success",
    }


def make_recording_handler(monkeypatch):
    requests = []

    def route(request):
        requests.append(request)
        return httpx.Response(200)

    transport = httpx.MockTransport(route)
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport)
    )
    return PushHandler(), requests


def test_sandbox_flag_targets_development_server(monkeypatch):
    monkeypatch.setenv("APNS_USE_SANDBOX", "true")
    handler, requests = make_recording_handler(monkeypatch)

    handler.send_push("device-token", body="hello")

    assert requests[0].url.host == "api.development.push.apple.com"


def test_production_server_is_default(monkeypatch):
    monkeypatch.delenv("APNS_USE_SANDBOX", raising=False)
    handler, requests = make_recording_handler(monkeypatch)

    handler.send_push("device-token", body="hello")

    assert requests[0].url.host == "api.push.apple.com"


def test_network_failure_for_one_token_does_not_block_others(monkeypatch):
    def route(request):
        token = request.url.path.rsplit("/", 1)[-1]
        if token == "unreachable-token":
            raise httpx.ConnectError("connection dropped")
        return httpx.Response(200)

    transport = httpx.MockTransport(route)
    real_client = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: real_client(transport=transport)
    )
    handler = PushHandler()

    results = handler.send_multiple_push(
        to_device_tokens=["good-token", "unreachable-token", "other-token"],
        body="hello",
    )

    assert results["good-token"] == "Success"
    assert results["unreachable-token"] == "ConnectionFailed"
    assert results["other-token"] == "Success"


def test_duplicate_recipients_are_sent_only_once(monkeypatch):
    handler, requests = make_recording_handler(monkeypatch)

    results = handler.send_multiple_push(
        to_device_tokens=["token-1", "token-1", "token-2"], body="hello"
    )

    assert len(requests) == 2
    assert results == {"token-1": "Success", "token-2": "Success"}


def test_sandbox_flag_tolerates_surrounding_whitespace(monkeypatch):
    monkeypatch.setenv("APNS_USE_SANDBOX", "true ")
    handler, requests = make_recording_handler(monkeypatch)

    handler.send_push("device-token", body="hello")

    assert requests[0].url.host == "api.development.push.apple.com"


def test_unrecognized_sandbox_value_is_rejected(monkeypatch):
    monkeypatch.setenv("APNS_USE_SANDBOX", "banana")

    with pytest.raises(ValueError):
        PushHandler()
