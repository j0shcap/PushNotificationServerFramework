"""Machinery for booting the real server as a subprocess during integration tests.

The server is launched exactly as the README documents (`python main.py`), so
the entrypoint, startup schema creation, and graceful shutdown are all under
test. `boot_server` waits for `/health` and asserts a clean SIGINT shutdown on
exit; `boot_expecting_startup_failure` asserts a fast non-zero exit instead,
for tests that boot deliberately misconfigured servers.
"""

import contextlib
import os
import secrets
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
import sqlalchemy

REPO_ROOT = Path(__file__).parent.parent.parent
API_KEY = secrets.token_hex(16)

STARTUP_TIMEOUT = 20
SHUTDOWN_TIMEOUT = 15


def integration_env() -> dict[str, str]:
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
    env.pop("CORS_ORIGINS", None)
    return env


def drop_devices_table(env: dict[str, str]) -> None:
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


@dataclass
class Server:
    """A running server subprocess and how to reach it."""

    process: subprocess.Popen[bytes]
    base_url: str
    log_path: Path

    def logs(self) -> str:
        return self.log_path.read_text()

    def stop(self) -> int:
        """Request graceful shutdown (SIGINT) and return the exit code."""
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=SHUTDOWN_TIMEOUT)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
                pytest.fail(f"server did not shut down within {SHUTDOWN_TIMEOUT}s:\n{self.logs()}")
        return self.process.returncode


@contextlib.contextmanager
def boot_server(tmp_dir: Path, env: dict[str, str] | None = None) -> Iterator[Server]:
    """Boot `python main.py` and wait until `/health` answers.

    Yields a Server; on exit the server is shut down with SIGINT and a clean
    exit code is asserted, so graceful shutdown is verified on every boot.
    """
    env = env or integration_env()
    port = _free_port()
    env["PORT"] = str(port)

    # Server output goes to a file, not a pipe: an undrained pipe blocks the
    # server once its buffer fills, which would hang the suite as it grows.
    log_path = tmp_dir / f"server-{port}.log"
    with open(log_path, "w") as log_file:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=REPO_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        server = Server(process, f"http://127.0.0.1:{port}", log_path)
        try:
            deadline = time.monotonic() + STARTUP_TIMEOUT
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail(f"server exited during startup:\n{server.logs()}")
                try:
                    if httpx.get(f"{server.base_url}/health", timeout=1).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.2)
            else:
                pytest.fail(f"server did not become healthy within {STARTUP_TIMEOUT}s")

            yield server
        finally:
            returncode = server.stop()
    assert returncode == 0, f"unclean shutdown (exit {returncode}):\n{server.logs()}"


def boot_expecting_startup_failure(tmp_dir: Path, env: dict[str, str]) -> str:
    """Boot the server with a broken environment and return its log output.

    Fails the test if the process serves traffic or survives past the startup
    window instead of exiting with a non-zero code.
    """
    port = _free_port()
    env["PORT"] = str(port)
    log_path = tmp_dir / f"server-fail-{port}.log"
    with open(log_path, "w") as log_file:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=REPO_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        try:
            process.wait(timeout=STARTUP_TIMEOUT)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            pytest.fail(f"server kept running despite broken config:\n{log_path.read_text()}")
    assert process.returncode != 0, "expected startup to fail with a non-zero exit code"
    return log_path.read_text()
