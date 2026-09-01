"""Fixtures for integration tests: the real server against real Postgres.

One server (booted by server_harness.boot_server) is shared by the whole
session; tests that need a different environment or a restart boot their own
via the harness. Tests require a reachable Postgres instance configured via
the INTEGRATION_DB_* environment variables and are skipped when
INTEGRATION_DB_HOST is not set.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from tests.integration.server_harness import (
    API_KEY,
    boot_server,
    drop_devices_table,
    integration_env,
)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # The hook receives every collected item, not just this directory's.
    integration_dir = Path(__file__).parent
    skip = pytest.mark.skipif(
        not os.getenv("INTEGRATION_DB_HOST"),
        reason="INTEGRATION_DB_HOST not set; see README for running integration tests",
    )
    for item in items:
        if integration_dir in item.path.parents:
            item.add_marker(pytest.mark.integration)
            item.add_marker(skip)


@pytest.fixture(scope="session")
def server_tmp_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.mktemp("integration-servers")


@pytest.fixture(scope="session")
def server(server_tmp_dir: Path) -> Iterator[str]:
    """One real server shared by the whole session, on a fresh database."""
    env = integration_env()
    drop_devices_table(env)
    with boot_server(server_tmp_dir, env) as running:
        yield running.base_url


@pytest.fixture
def clean_devices(server: str) -> None:
    """Start every test from an empty devices table, so tests stay
    order-independent as the suite grows."""
    response = httpx.delete(
        f"{server}/devices", headers={"Authorization": f"Bearer {API_KEY}"}, timeout=5
    )
    assert response.status_code == 200


@pytest.fixture
def api(server: str, clean_devices: None) -> Iterator[httpx.Client]:
    """HTTP client authenticated with the server's API key."""
    with httpx.Client(base_url=server, headers={"Authorization": f"Bearer {API_KEY}"}) as client:
        yield client


@pytest.fixture
def anon_api(server: str, clean_devices: None) -> Iterator[httpx.Client]:
    """HTTP client with no credentials."""
    with httpx.Client(base_url=server) as client:
        yield client


BAD_AUTHORIZATIONS: dict[str, str] = {
    "wrong key": "Bearer wrong-key",
    "truncated key": f"Bearer {API_KEY[:-1]}",
    "wrong case key": f"Bearer {API_KEY.upper()}",
    "wrong scheme": f"Basic {API_KEY}",
    "scheme only": "Bearer",
    "key without scheme": API_KEY,
}


@pytest.fixture(params=BAD_AUTHORIZATIONS.values(), ids=BAD_AUTHORIZATIONS.keys())
def bad_authorization(request: pytest.FixtureRequest) -> str:
    """Authorization header values that must never authenticate."""
    return request.param
