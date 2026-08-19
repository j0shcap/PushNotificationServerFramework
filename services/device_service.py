from entities import DeviceEntity
from models import Device
from sqlalchemy import delete, select
from database import db_session
from sqlalchemy.orm import Session
from fastapi import Depends


class DeviceService:
    """
    A service for registering and managing devices.

    Attributes:
        session (Session): The database session to use. Injected by FastAPI.

    Methods:
        register_device(device: Device) -> Device: Register a device.
        get_registered_devices() -> list[Device]: Get all registered devices.
        clear_registered_devices() -> None: Clear all registered devices.
    """

    def __init__(self, session: Session = Depends(db_session)):
        """
        Initialize the DeviceService.

        Args:
            session (Session): The database session to use. Injected by FastAPI.
        """
        self._session = session

    def register_device(self, device: Device) -> Device:
        """
        Register a device, updating its information if the token is already registered.

        Device tokens change across app reinstalls and OS restores, so clients
        re-register on every launch; registration must therefore be idempotent.
        Clients often re-register with only the token, so stored fields are
        preserved unless the request provides a new value.

        Args:
            device (Device): The device to register.

        Returns:
            Device: The registered device.
        """
        device_entity = self._session.scalar(
            select(DeviceEntity).where(DeviceEntity.token == device.token)
        )
        if device_entity:
            for field in ("name", "systemName", "systemVersion", "model", "localizedModel"):
                value = getattr(device, field)
                if value is not None:
                    setattr(device_entity, field, value)
        else:
            device_entity = DeviceEntity.from_model(device)
            self._session.add(device_entity)
        self._session.commit()
        return device_entity.to_model()

    def get_registered_devices(self) -> list[Device]:
        """
        Get all registered devices.

        Returns:
            list[Device]: A list of Device objects representing all registered devices.
        """
        devices = self._session.execute(select(DeviceEntity)).scalars().all()
        return [device.to_model() for device in devices]

    def remove_devices(self, tokens: list[str]) -> None:
        """
        Remove the devices with the given tokens, if they exist.

        Args:
            tokens (list[str]): The device tokens to remove.
        """
        if not tokens:
            return
        self._session.execute(delete(DeviceEntity).where(DeviceEntity.token.in_(tokens)))
        self._session.commit()

    def clear_registered_devices(self) -> None:
        """
        Clear all registered devices.

        This method deletes all registered devices from the database.
        """
        self._session.execute(delete(DeviceEntity))
        self._session.commit()
