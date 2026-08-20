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


def make_raw_client(monkeypatch, status_code, text):
    transport = httpx.MockTransport(lambda request: httpx.Response(status_code, text=text))
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=transport))
    credentials = TokenCredentials(
        auth_key_path=KEY_PATH, auth_key_id="TESTKEY123", team_id="TESTTEAM12"
    )
    return APNsClient(credentials=credentials)


def test_410_without_json_body_still_reports_unregistered(monkeypatch):
    client = make_raw_client(monkeypatch, 410, "gone")

    with pytest.raises(Unregistered):
        client.send_notification("stale-token", Payload(alert="hello"), topic="com.example.test")


def test_non_json_error_body_is_not_leaked_as_reason(monkeypatch):
    client = make_raw_client(monkeypatch, 502, "<html>Bad Gateway from some proxy</html>")

    with pytest.raises(APNsException) as exc_info:
        client.send_notification("device-token", Payload(alert="hello"), topic="com.example.test")

    assert "<html>" not in str(exc_info.value)


def test_raised_exception_message_carries_the_reason(monkeypatch):
    client = make_client(monkeypatch, 400, {"reason": "SomeFutureReason"})

    with pytest.raises(APNsException) as exc_info:
        client.send_notification("device-token", Payload(alert="hello"), topic="com.example.test")

    assert "SomeFutureReason" in str(exc_info.value)


def test_json_error_body_without_reason_key_maps_to_status_marker(monkeypatch):
    client = make_client(monkeypatch, 400, {"timestamp": "1700000000"})

    with pytest.raises(APNsException) as exc_info:
        client.send_notification("device-token", Payload(alert="hello"), topic="com.example.test")

    assert "HTTPError400" in str(exc_info.value)


def test_non_dict_json_error_body_maps_to_status_marker(monkeypatch):
    client = make_raw_client(monkeypatch, 503, '"Service Unavailable"')

    with pytest.raises(APNsException) as exc_info:
        client.send_notification("device-token", Payload(alert="hello"), topic="com.example.test")

    assert "HTTPError503" in str(exc_info.value)


def test_new_apns_reasons_map_to_typed_exceptions(monkeypatch):
    from push.apn_handler.errors import InvalidPushType

    client = make_client(monkeypatch, 400, {"reason": "InvalidPushType"})

    with pytest.raises(InvalidPushType):
        client.send_notification("device-token", Payload(alert="hello"), topic="com.example.test")


def test_live_activity_topic_infers_liveactivity_push_type(monkeypatch):
    requests = []
    client = make_client(monkeypatch, 200, {}, requests)

    client.send_notification(
        "device-token",
        Payload(alert="hello"),
        topic="com.example.test.push-type.liveactivity",
    )

    assert requests[0].headers["apns-push-type"] == "liveactivity"


def test_optional_headers_are_sent_when_specified(monkeypatch):
    from push.apn_handler.client import NotificationPriority

    requests = []
    client = make_client(monkeypatch, 200, {}, requests)

    client.send_notification(
        "device-token",
        Payload(alert="hello"),
        topic="com.example.test",
        priority=NotificationPriority.Delayed,
        expiration=0,
        collapse_id="thread-1",
    )

    headers = requests[0].headers
    assert headers["apns-priority"] == "5"
    assert headers["apns-expiration"] == "0"
    assert headers["apns-collapse-id"] == "thread-1"


def test_default_priority_sends_no_priority_header(monkeypatch):
    requests = []
    client = make_client(monkeypatch, 200, {}, requests)

    client.send_notification("device-token", Payload(alert="hello"), topic="com.example.test")

    assert "apns-priority" not in requests[0].headers


def test_silent_payload_infers_background_push_type(monkeypatch):
    requests = []
    client = make_client(monkeypatch, 200, {}, requests)

    client.send_notification(
        "device-token", Payload(content_available=True), topic="com.example.test"
    )

    assert requests[0].headers["apns-push-type"] == "background"


def test_no_topic_sends_no_topic_or_push_type_headers(monkeypatch):
    requests = []
    client = make_client(monkeypatch, 200, {}, requests)

    client.send_notification("device-token", Payload(alert="hello"))

    assert "apns-topic" not in requests[0].headers
    assert "apns-push-type" not in requests[0].headers


def test_expired_token_maps_to_typed_exception(monkeypatch):
    from push.apn_handler.errors import ExpiredToken

    client = make_client(monkeypatch, 410, {"reason": "ExpiredToken", "timestamp": "1700000000"})

    with pytest.raises(ExpiredToken):
        client.send_notification("dead-token", Payload(alert="hello"), topic="com.example.test")
