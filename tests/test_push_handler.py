"""Tests for PushHandler, with the HTTP layer mocked per device token."""

import httpx

from push import PushHandler


def make_handler(monkeypatch, responses_by_token):
    """Build a PushHandler whose APNs response depends on the device token."""

    def route(request):
        token = request.url.path.rsplit("/", 1)[-1]
        status_code, body = responses_by_token[token]
        return httpx.Response(status_code, json=body)

    transport = httpx.MockTransport(route)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=transport))
    return PushHandler()


def test_send_multiple_push_returns_result_per_token(monkeypatch):
    handler = make_handler(
        monkeypatch,
        {
            "good-token": (200, {}),
            "stale-token": (410, {"reason": "Unregistered", "timestamp": "1700000000"}),
            "other-token": (200, {}),
        },
    )

    results = handler.send_multiple_push(
        to_device_tokens=["good-token", "stale-token", "other-token"], body="hello"
    )

    assert results == {
        "good-token": "Success",
        "stale-token": "Unregistered",
        "other-token": "Success",
    }
