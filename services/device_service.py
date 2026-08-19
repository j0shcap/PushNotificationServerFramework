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
        Register a device.

        Args:
            device (Device): The device to register.

        Returns:
            Device: The registered device.
        """
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

    def clear_registered_devices(self) -> None:
        """
        Clear all registered devices.

        This method deletes all registered devices from the database.
        """
        self._session.execute(delete(DeviceEntity))
        self._session.commit()
