"""Tests for the /devices endpoints."""


def test_register_device_returns_device_with_id(client):
    response = client.post("/devices/register", json={"token": "abc123"})

    assert response.status_code == 200
    body = response.json()
    assert body["token"] == "abc123"
    assert body["id"] is not None


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
