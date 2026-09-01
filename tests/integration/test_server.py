"""Integration tests: the real server process against a real Postgres database.

These drive the shared server (see conftest.py) over HTTP with no test
doubles, covering the device lifecycle, authentication, input validation,
and concurrent access.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx
import pytest


class TestHealthAndRouting:
    def test_health_and_root_are_public(self, anon_api: httpx.Client) -> None:
        assert anon_api.get("/health").json() == {"message": "OK"}
        assert anon_api.get("/").json() == {"message": "Hello World"}

    def test_openapi_schema_is_served(self, anon_api: httpx.Client) -> None:
        schema = anon_api.get("/openapi.json")
        assert schema.status_code == 200
        paths = schema.json()["paths"]
        assert "/devices/register" in paths
        assert "/push/send" in paths

    def test_unknown_route_is_404(self, api: httpx.Client) -> None:
        assert api.get("/devices/nope").status_code == 404

    def test_wrong_method_is_405(self, api: httpx.Client) -> None:
        assert api.get("/push/send").status_code == 405

    def test_old_clear_route_is_gone(self, api: httpx.Client) -> None:
        assert api.get("/devices/clear").status_code in (404, 405)

    def test_cors_headers_absent_when_cors_not_configured(self, anon_api: httpx.Client) -> None:
        response = anon_api.get("/health", headers={"Origin": "http://evil.example"})
        assert "access-control-allow-origin" not in response.headers


class TestDeviceLifecycle:
    def test_startup_creates_schema_and_serves_devices(self, api: httpx.Client) -> None:
        assert api.get("/devices/all").status_code == 200

    def test_device_lifecycle(self, api: httpx.Client, anon_api: httpx.Client) -> None:
        registered = anon_api.post(
            "/devices/register",
            json={"token": "integration-token", "name": "Integration Phone"},
        )
        assert registered.status_code == 200
        body = registered.json()
        assert body["id"] is not None
        assert body["created_at"] is not None

        reregistered = anon_api.post(
            "/devices/register", json={"token": "integration-token", "systemVersion": "18.0"}
        )
        assert reregistered.status_code == 200
        assert reregistered.json()["id"] == body["id"]
        assert reregistered.json()["name"] == "Integration Phone"
        assert reregistered.json()["systemVersion"] == "18.0"

        tokens = {device["token"] for device in api.get("/devices/all").json()}
        assert "integration-token" in tokens

        assert api.delete("/devices").status_code == 200
        assert api.get("/devices/all").json() == []

    def test_reregistration_preserves_created_at_and_identity(
        self, anon_api: httpx.Client
    ) -> None:
        first = anon_api.post("/devices/register", json={"token": "stable-token"}).json()
        second = anon_api.post(
            "/devices/register", json={"token": "stable-token", "name": "Named later"}
        ).json()

        assert second["id"] == first["id"]
        assert second["created_at"] == first["created_at"]
        assert second["name"] == "Named later"

    def test_full_device_metadata_round_trips(
        self, api: httpx.Client, anon_api: httpx.Client
    ) -> None:
        registration = {
            "token": "full-token",
            "name": "Josh’s iPhone \N{MOBILE PHONE}",
            "systemName": "iOS",
            "systemVersion": "18.4.1",
            "model": "iPhone",
            "localizedModel": "iPhone",
        }
        registered = anon_api.post("/devices/register", json=registration)
        assert registered.status_code == 200

        (stored,) = api.get("/devices/all").json()
        for field, value in registration.items():
            assert stored[field] == value

    def test_many_devices_are_all_listed(
        self, api: httpx.Client, anon_api: httpx.Client
    ) -> None:
        for i in range(25):
            response = anon_api.post("/devices/register", json={"token": f"bulk-token-{i}"})
            assert response.status_code == 200

        tokens = {device["token"] for device in api.get("/devices/all").json()}
        assert tokens == {f"bulk-token-{i}" for i in range(25)}

    def test_clear_devices_is_idempotent(self, api: httpx.Client) -> None:
        assert api.delete("/devices").status_code == 200
        assert api.delete("/devices").status_code == 200
        assert api.get("/devices/all").json() == []


class TestRegistrationValidation:
    @pytest.mark.parametrize(
        "registration",
        [
            {"name": "no token"},
            {"token": ""},
            {"token": 12345},
            {"token": "a" * 256},
        ],
        ids=["missing token", "empty token", "non-string token", "token over column limit"],
    )
    def test_invalid_registration_is_rejected_and_stores_nothing(
        self, api: httpx.Client, anon_api: httpx.Client, registration: dict[str, Any]
    ) -> None:
        response = anon_api.post("/devices/register", json=registration)

        assert response.status_code == 422
        assert api.get("/devices/all").json() == []

    def test_malformed_json_is_rejected(self, anon_api: httpx.Client) -> None:
        response = anon_api.post(
            "/devices/register",
            content=b'{"token": ',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_unknown_fields_are_ignored_not_stored(self, anon_api: httpx.Client) -> None:
        response = anon_api.post(
            "/devices/register", json={"token": "extra-token", "id": 999999, "isAdmin": True}
        )
        assert response.status_code == 200
        assert response.json()["id"] != 999999
        assert "isAdmin" not in response.json()

    def test_token_at_column_limit_round_trips(
        self, api: httpx.Client, anon_api: httpx.Client
    ) -> None:
        token = "a" * 255

        assert anon_api.post("/devices/register", json={"token": token}).status_code == 200
        assert [device["token"] for device in api.get("/devices/all").json()] == [token]


class TestAuthentication:
    def test_protected_routes_require_credentials(
        self, anon_api: httpx.Client, protected_route: tuple[str, str]
    ) -> None:
        method, path = protected_route

        response = anon_api.request(method, path, json={"recipients": [], "body": "x"})

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    def test_rejected_credentials(
        self, anon_api: httpx.Client, protected_route: tuple[str, str], bad_authorization: str
    ) -> None:
        method, path = protected_route

        response = anon_api.request(
            method,
            path,
            json={"recipients": [], "body": "x"},
            headers={"Authorization": bad_authorization},
        )

        assert response.status_code == 401

    def test_registration_does_not_require_credentials(self, anon_api: httpx.Client) -> None:
        response = anon_api.post("/devices/register", json={"token": "anon-token"})
        assert response.status_code == 200

    def test_health_ignores_bad_credentials(self, anon_api: httpx.Client) -> None:
        response = anon_api.get("/health", headers={"Authorization": "Bearer wrong"})
        assert response.status_code == 200


class TestPush:
    def test_push_send_with_no_recipients_succeeds_authenticated(self, api: httpx.Client) -> None:
        response = api.post("/push/send", json={"recipients": [], "body": "hello"})

        assert response.status_code == 200
        assert response.json() == {}

    @pytest.mark.parametrize(
        "message",
        [
            {"body": "hello"},
            {"recipients": []},
            {"recipients": "not-a-list", "body": "x"},
        ],
        ids=["missing recipients", "missing body", "non-list recipients"],
    )
    def test_invalid_push_message_is_rejected(
        self, api: httpx.Client, message: dict[str, Any]
    ) -> None:
        assert api.post("/push/send", json=message).status_code == 422


class TestConcurrency:
    def test_concurrent_registration_of_same_token_yields_one_device(
        self, api: httpx.Client, anon_api: httpx.Client
    ) -> None:
        def register(i: int) -> httpx.Response:
            return anon_api.post(
                "/devices/register", json={"token": "race-token", "name": f"racer-{i}"}
            )

        with ThreadPoolExecutor(max_workers=16) as pool:
            responses = list(pool.map(register, range(16)))

        assert all(response.status_code == 200 for response in responses)
        assert len({response.json()["id"] for response in responses}) == 1
        devices = api.get("/devices/all").json()
        assert [device["token"] for device in devices] == ["race-token"]

    def test_concurrent_registration_of_distinct_tokens_stores_all(
        self, api: httpx.Client, server: str
    ) -> None:
        def register(i: int) -> httpx.Response:
            with httpx.Client(base_url=server, timeout=10) as client:
                return client.post("/devices/register", json={"token": f"parallel-token-{i}"})

        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(register, range(24)))

        assert all(response.status_code == 200 for response in responses)
        tokens = {device["token"] for device in api.get("/devices/all").json()}
        assert tokens == {f"parallel-token-{i}" for i in range(24)}

    def test_concurrent_reads_during_writes_stay_consistent(
        self, api: httpx.Client, anon_api: httpx.Client
    ) -> None:
        def hammer(i: int) -> httpx.Response:
            if i % 2:
                return anon_api.post("/devices/register", json={"token": f"mixed-token-{i}"})
            return api.get("/devices/all")

        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(hammer, range(20)))

        assert all(response.status_code == 200 for response in responses)
