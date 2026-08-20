"""End-to-end tests against Apple's real APNs sandbox.

These make real network calls to api.sandbox.push.apple.com, so they are
opt-in: set APNS_SANDBOX_E2E=1 to run them. They use whatever APNs credentials
the environment provides (the checked-in throwaway key by default).

The connectivity test passes with any well-formed credentials: Apple's
response proves DNS, TLS, HTTP/2, JWT signing, and response parsing regardless
of whether the key is registered. Verifying actual delivery additionally
requires real credentials and a sandbox device token from a development build,
supplied via APNS_E2E_DEVICE_TOKEN.
"""

import os

import pytest

from push import PushHandler
from push.apn_handler.errors import REASON_TO_EXCEPTION

pytestmark = [
    pytest.mark.apns_sandbox,
    pytest.mark.skipif(
        not os.getenv("APNS_SANDBOX_E2E"),
        reason="APNS_SANDBOX_E2E not set; these tests call Apple's real sandbox",
    ),
]


@pytest.fixture
def sandbox_handler(monkeypatch):
    """A PushHandler pinned to the sandbox, regardless of ambient environment."""
    monkeypatch.setenv("APNS_USE_SANDBOX", "true")
    handler = PushHandler()
    yield handler
    handler.close()


def test_sandbox_round_trip_returns_a_reason_apple_defines(sandbox_handler):
    results = sandbox_handler.send_multiple_push(
        to_device_tokens=["deadbeef00"], body="e2e connectivity check"
    )

    result = results["deadbeef00"]
    # Any documented reason (or Success) proves the request reached Apple and
    # was parsed; transport failures and unparseable responses surface as
    # "ConnectionFailed" or "HTTPError<status>" instead and must fail here.
    assert result == "Success" or result in REASON_TO_EXCEPTION


def test_delivery_to_real_device(sandbox_handler):
    device_token = os.getenv("APNS_E2E_DEVICE_TOKEN")
    if not device_token:
        pytest.skip("APNS_E2E_DEVICE_TOKEN not set; needs real credentials and a device")

    results = sandbox_handler.send_multiple_push(
        to_device_tokens=[device_token], body="PushNotificationServerFramework delivery test"
    )

    assert results == {device_token: "Success"}
