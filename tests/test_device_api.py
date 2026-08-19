"""Tests for the /devices endpoints."""


def test_register_device_returns_device_with_id(client):
    response = client.post("/devices/register", json={"token": "abc123"})

    assert response.status_code == 200
    body = response.json()
    assert body["token"] == "abc123"
    assert body["id"] is not None
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


def test_register_device_stores_optional_fields(client):
    response = client.post(
        "/devices/register",
        json={"token": "abc123", "name": "Josh's iPhone", "systemVersion": "17.0"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Josh's iPhone"
    assert body["systemVersion"] == "17.0"


def test_register_device_without_token_is_rejected(client):
    response = client.post("/devices/register", json={"name": "no token"})

    assert response.status_code == 422


def test_get_all_devices_returns_registered_devices(client):
    client.post("/devices/register", json={"token": "token-1"})
    client.post("/devices/register", json={"token": "token-2"})

    response = client.get("/devices/all")

    assert response.status_code == 200
    tokens = {device["token"] for device in response.json()}
    assert tokens == {"token-1", "token-2"}


def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200


def test_clear_removes_all_registered_devices(client):
    client.post("/devices/register", json={"token": "token-1"})
    client.post("/devices/register", json={"token": "token-2"})

    response = client.get("/devices/clear")

    assert response.status_code == 200
    assert client.get("/devices/all").json() == []


def test_register_same_token_twice_updates_existing_device(client):
    first = client.post(
        "/devices/register", json={"token": "abc123", "systemVersion": "17.0"}
    )
    second = client.post(
        "/devices/register", json={"token": "abc123", "systemVersion": "18.1"}
    )

    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["systemVersion"] == "18.1"

    devices = client.get("/devices/all").json()
    assert len(devices) == 1


def test_reregistering_with_only_token_preserves_stored_fields(client):
    client.post(
        "/devices/register",
        json={"token": "abc123", "name": "Josh's iPhone", "systemVersion": "17.0"},
    )

    response = client.post("/devices/register", json={"token": "abc123"})

    assert response.status_code == 200
    assert response.json()["name"] == "Josh's iPhone"
    assert response.json()["systemVersion"] == "17.0"


def test_concurrent_registration_race_falls_back_to_update(test_engine):
    from sqlalchemy.orm import Session

    from models import Device
    from services import DeviceService

    with Session(test_engine) as session:
        DeviceService(session=session).register_device(Device(token="abc123", name="winner"))

    with Session(test_engine) as session:
        service = DeviceService(session=session)
        real_scalar = session.scalar
        calls = []

        def stale_scalar(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                return None
            return real_scalar(*args, **kwargs)

        session.scalar = stale_scalar
        result = service.register_device(Device(token="abc123", name="loser"))

    assert result.name == "loser"
    with Session(test_engine) as session:
        devices = DeviceService(session=session).get_registered_devices()
    assert len(devices) == 1
