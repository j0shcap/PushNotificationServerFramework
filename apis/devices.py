from fastapi import APIRouter, Depends

from models import Device
from services import DeviceService

router = APIRouter(
    prefix="/devices",
    tags=["devices"],
    responses={404: {"description": "Not found"}},
)


@router.post("/register", response_model=Device)
def register_device(device: Device, device_service: DeviceService = Depends()):
    """
    Registers a new device with the push notification framework.

    Args:
        device (Device): The device to register.
        device_service (DeviceService): An instance of the DeviceService class. Injected by FastAPI.

    Returns:
        Device: The registered device.
    """
    return device_service.register_device(device)


@router.get("/all", response_model=list[Device])
def get_registered_devices(
    device_service: DeviceService = Depends(),
):
    """
    Retrieve a list of all registered devices.

    Args:
        device_service (DeviceService): An instance of the DeviceService class. Injected by FastAPI.

    Returns:
        list[Device]: A list of Device objects representing all registered devices.
    """
    return device_service.get_registered_devices()


# FOR TESTING PURPOSES ONLY
@router.get("/clear", response_model=None)
def clear_registered_devices(
    device_service: DeviceService = Depends(),
):
    """
    Clears all registered devices from the device service.
    """
    return device_service.clear_registered_devices()
