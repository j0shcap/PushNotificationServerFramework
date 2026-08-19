"""Tests for APNs token credentials."""

from pathlib import Path

import jwt
from cryptography.hazmat.primitives.serialization import load_pem_private_key

from push.apn_handler import TokenCredentials

KEY_PATH = str(Path(__file__).parent / "fixtures" / "apns_test_key.p8")


def make_credentials(**kwargs):
    return TokenCredentials(
        auth_key_path=KEY_PATH,
        auth_key_id="TESTKEY123",
        team_id="TESTTEAM12",
        **kwargs,
    )


def test_authorization_header_contains_signed_es256_jwt():
    header = make_credentials().get_authorization_header("com.example.test")

    assert header.startswith("bearer ")
    token = header.removeprefix("bearer ")

    unverified_header = jwt.get_unverified_header(token)
    assert unverified_header["alg"] == "ES256"
    assert unverified_header["kid"] == "TESTKEY123"

    with open(KEY_PATH, "rb") as key_file:
        public_key = load_pem_private_key(key_file.read(), password=None).public_key()
    claims = jwt.decode(token, public_key, algorithms=["ES256"])
    assert claims["iss"] == "TESTTEAM12"


def test_token_is_reused_until_expiry():
    credentials = make_credentials()

    first = credentials.get_authorization_header("com.example.test")
    second = credentials.get_authorization_header("com.example.test")

    assert first == second
