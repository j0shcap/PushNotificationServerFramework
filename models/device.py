from datetime import datetime

from pydantic import BaseModel, Field


class DeviceRegistration(BaseModel):
    """
    Client-supplied device information for registration.

    Attributes:
        token (str): The device token used for push notifications. Required.
        name (str): The name of the device.
        systemName (str): The name of the operating system running on the device.
        systemVersion (str): The version of the operating system running on the device.
        model (str): The model of the device.
        localizedModel (str): The localized model of the device.
    """

    # Bounded to the devices.token column (String(255)) so oversized input
    # fails validation instead of raising a database error.
    token: str = Field(min_length=1, max_length=255)
    name: str | None = None
    systemName: str | None = None
    systemVersion: str | None = None
    model: str | None = None
    localizedModel: str | None = None


class Device(DeviceRegistration):
    """
    A registered device, including server-managed fields.

    Attributes:
        id (int): The unique identifier for the device. Assigned by the server.
        created_at (datetime | None): When the device was first registered.
        updated_at (datetime | None): When the device was last updated.
    """

    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
