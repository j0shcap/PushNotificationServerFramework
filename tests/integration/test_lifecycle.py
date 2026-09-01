"""Integration tests for server lifecycle: restarts, startup failures, CORS.

Each test here boots its own server subprocess (or several) rather than using
the session-wide one, because they exercise boot-time behavior: schema
creation against an existing database, refusing to start on broken
configuration, and CORS middleware wiring from the environment.
"""

from pathlib import Path

import httpx

from tests.integration.server_harness import (
    API_KEY,
    boot_expecting_startup_failure,
    boot_server,
    integration_env,
)


def test_data_survives_a_server_restart(server_tmp_dir: Path) -> None:
    # Cleared through the API rather than dropped: the session-wide server
    # shares this database and must keep its table.
    env = integration_env()

    with boot_server(server_tmp_dir, dict(env)) as first:
        auth = {"Authorization": f"Bearer {API_KEY}"}
        assert httpx.delete(f"{first.base_url}/devices", headers=auth).status_code == 200
        response = httpx.post(
            f"{first.base_url}/devices/register",
            json={"token": "durable-token", "name": "Survivor"},
        )
        assert response.status_code == 200

    with boot_server(server_tmp_dir, dict(env)) as second:
        devices = httpx.get(
            f"{second.base_url}/devices/all",
            headers={"Authorization": f"Bearer {API_KEY}"},
        ).json()
        assert [(device["token"], device["name"]) for device in devices] == [
            ("durable-token", "Survivor")
        ]


def test_startup_fails_fast_without_api_key(server_tmp_dir: Path) -> None:
    env = integration_env()
    del env["API_KEY"]

    logs = boot_expecting_startup_failure(server_tmp_dir, env)

    assert "API_KEY environment variable must be set" in logs


def test_startup_rejects_wildcard_cors_origins(server_tmp_dir: Path) -> None:
    env = integration_env()
    env["CORS_ORIGINS"] = "https://app.example.com, *"

    logs = boot_expecting_startup_failure(server_tmp_dir, env)

    assert "CORS_ORIGINS must list explicit origins" in logs


def test_cors_configured_server_only_allows_listed_origins(server_tmp_dir: Path) -> None:
    env = integration_env()
    env["CORS_ORIGINS"] = "https://app.example.com"

    with boot_server(server_tmp_dir, env) as running:
        preflight = httpx.options(
            f"{running.base_url}/devices/all",
            headers={
                "Origin": "https://app.example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-origin"] == "https://app.example.com"
        assert preflight.headers["access-control-allow-credentials"] == "true"

        cross_origin_get = httpx.get(
            f"{running.base_url}/health", headers={"Origin": "https://app.example.com"}
        )
        assert cross_origin_get.headers["access-control-allow-origin"] == "https://app.example.com"

        rejected_preflight = httpx.options(
            f"{running.base_url}/devices/all",
            headers={
                "Origin": "https://evil.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert "access-control-allow-origin" not in rejected_preflight.headers
