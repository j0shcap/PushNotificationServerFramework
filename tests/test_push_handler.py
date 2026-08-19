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
