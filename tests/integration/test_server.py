"""Integration tests: the real server process against a real Postgres database.

These boot `uvicorn main:app` as a subprocess and drive it over HTTP, so they
cover startup schema creation, authentication, the full device lifecycle, and
graceful shutdown with no test doubles. They require a reachable Postgres
instance, configured via INTEGRATION_DB_* environment variables (see README),
and are skipped when INTEGRATION_DB_HOST is not set.
"""

import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
import sqlalchemy

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not os.getenv("INTEGRATION_DB_HOST"),
        reason="INTEGRATION_DB_HOST not set; see README for running integration tests",
    ),
]

REPO_ROOT = Path(__file__).parent.parent.parent
API_KEY = secrets.token_hex(16)


def _integration_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "DB_HOST": os.environ["INTEGRATION_DB_HOST"],
            "DB_PORT": os.environ.get("INTEGRATION_DB_PORT", "5432"),
            "DB_NAME": os.environ.get("INTEGRATION_DB_NAME", "postgres"),
            "DB_USERNAME": os.environ.get("INTEGRATION_DB_USERNAME", "postgres"),
            "DB_PASSWORD": os.environ.get("INTEGRATION_DB_PASSWORD", "postgres"),
            "API_KEY": API_KEY,
            "APNS_KEY_ID": "TESTKEY123",
            "APNS_TEAM_ID": "TESTTEAM12",
            "APNS_APP_BUNDLE_ID": "com.example.test",
            "APNS_AUTH_KEY_PATH": str(REPO_ROOT / "tests" / "fixtures" / "apns_test_key.p8"),
            "APNS_USE_SANDBOX": "true",
        }
    )
    return env


def _drop_devices_table(env: dict[str, str]) -> None:
    url = (
        f"postgresql+psycopg2://{env['DB_USERNAME']}:{env['DB_PASSWORD']}"
        f"@{env['DB_HOST']}:{env['DB_PORT']}/{env['DB_NAME']}"
    )
    engine = sqlalchemy.create_engine(url)
    with engine.begin() as connection:
        connection.execute(sqlalchemy.text("DROP TABLE IF EXISTS devices"))
    engine.dispose()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """The real application booted as a subprocess against real Postgres."""
    env = _integration_env()
    _drop_devices_table(env)
    port = _free_port()
    env["PORT"] = str(port)

    # Server output goes to a file, not a pipe: an undrained pipe blocks the
    # server once its buffer fills, which would hang the suite as it grows.
    log_path = tmp_path_factory.mktemp("server") / "server.log"
    with open(log_path, "w") as log_file:
        # Launched exactly as the README documents, so the entrypoint itself
        # (including HOST/PORT handling) is part of what these tests cover.
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=REPO_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        base_url = f"http://127.0.0.1:{port}"
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail(f"server exited during startup:\n{log_path.read_text()}")
                try:
                    if httpx.get(f"{base_url}/health", timeout=1).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.2)
            else:
                pytest.fail("server did not become healthy within 20s")

            yield base_url
        finally:
            process.send_signal(signal.SIGINT)
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                pytest.fail("server did not shut down gracefully within 15s")
    assert process.returncode == 0, f"unclean shutdown:\n{log_path.read_text()}"


@pytest.fixture
def api(server):
    """HTTP client authenticated with the server's API key."""
    with httpx.Client(base_url=server, headers={"Authorization": f"Bearer {API_KEY}"}) as client:
        yield client


@pytest.fixture
def anon_api(server):
    """HTTP client with no credentials."""
    with httpx.Client(base_url=server) as client:
        yield client


def test_startup_creates_schema_and_serves_health(api):
    assert api.get("/health").json() == {"message": "OK"}
    assert api.get("/devices/all").status_code == 200


def test_device_lifecycle(api, anon_api):
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


def test_registration_rejects_missing_token(anon_api):
    assert anon_api.post("/devices/register", json={"name": "no token"}).status_code == 422


def test_protected_routes_require_credentials(anon_api, protected_route):
    method, path = protected_route

    response = anon_api.request(method, path, json={"recipients": [], "body": "x"})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_protected_routes_reject_wrong_key(server):
    with httpx.Client(base_url=server, headers={"Authorization": "Bearer wrong-key"}) as client:
        assert client.get("/devices/all").status_code == 401


def test_push_send_with_no_recipients_succeeds_authenticated(api):
    response = api.post("/push/send", json={"recipients": [], "body": "hello"})

    assert response.status_code == 200
    assert response.json() == {}


def test_old_clear_route_is_gone(api):
    assert api.get("/devices/clear").status_code in (404, 405)
