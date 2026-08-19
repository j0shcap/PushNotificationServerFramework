"""Tests for PushHandler, with the HTTP layer mocked per device token."""


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
    import httpx

    from push import PushHandler

    requests = []

    def route(request):
        requests.append(request)
        return httpx.Response(200)

    transport = httpx.MockTransport(route)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=transport))
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
