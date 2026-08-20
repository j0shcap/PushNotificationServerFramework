"""Tests for push credential configuration.

The certificate fixture is a self-signed cert generated for tests only; it
has never been presented to Apple.
"""

from pathlib import Path

import httpx
import pytest

from push import PushHandler
from push.apn_handler import CertificateCredentials, TokenCredentials
from push.config import PushConfig

CERT_PATH = str(Path(__file__).parent / "fixtures" / "apns_test_cert.pem")


def test_token_credentials_are_the_default(monkeypatch):
    monkeypatch.delenv("APNS_CERT_PATH", raising=False)

    assert isinstance(PushConfig.get_credentials(), TokenCredentials)


def test_certificate_credentials_when_cert_path_is_set(monkeypatch):
    monkeypatch.setenv("APNS_CERT_PATH", CERT_PATH)

    credentials = PushConfig.get_credentials()

    assert isinstance(credentials, CertificateCredentials)
    assert credentials.ssl_context is not None


def test_certificate_credentials_reject_missing_file():
    with pytest.raises(FileNotFoundError):
        CertificateCredentials("/nonexistent/cert.pem")


def test_certificate_auth_sends_no_authorization_header(monkeypatch):
    monkeypatch.setenv("APNS_CERT_PATH", CERT_PATH)
    requests = []

    def route(request):
        requests.append(request)
        return httpx.Response(200)

    transport = httpx.MockTransport(route)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=transport))
    handler = PushHandler()

    handler.send_push("device-token", body="hello")

    assert "authorization" not in requests[0].headers
    handler.close()


def test_token_auth_sends_authorization_header(monkeypatch):
    monkeypatch.delenv("APNS_CERT_PATH", raising=False)
    requests = []

    def route(request):
        requests.append(request)
        return httpx.Response(200)

    transport = httpx.MockTransport(route)
    real_client = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: real_client(transport=transport))
    handler = PushHandler()

    handler.send_push("device-token", body="hello")

    assert requests[0].headers["authorization"].startswith("bearer ")
    handler.close()
