from sqlalchemy import Column, DateTime, Integer, String, func

from models import Device

from .entity_base import EntityBase


class DeviceEntity(EntityBase):
    """
    Represents a device entity in the database.

    Attributes:
        id (int): The primary key of the device entity.
        token (str): The device token.
        name (str): The name of the device.
        systemName (str): The name of the operating system running on the device.
        systemVersion (str): The version of the operating system running on the device.
        model (str): The device model.
        localizedModel (str): The localized model of the device.
        created_at (datetime): The timestamp of when the device entity was created.
        updated_at (datetime): The timestamp of when the device entity was last updated.
    """

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), nullable=False, unique=True)
    name = Column(String(255), nullable=True)
    systemName = Column(String(255), nullable=True)
    systemVersion = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    localizedModel = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    def to_model(self) -> Device:
        return Device(
            id=self.id,
            token=self.token,
            name=self.name,
            systemName=self.systemName,
            systemVersion=self.systemVersion,
            model=self.model,
            localizedModel=self.localizedModel,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_model(cls, model: Device) -> "DeviceEntity":
        return cls(
            id=model.id,
            token=model.token,
            name=model.name,
            systemName=model.systemName,
            systemVersion=model.systemVersion,
            model=model.model,
            localizedModel=model.localizedModel,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
