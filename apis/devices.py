from fastapi import APIRouter, Depends

from models import Device
from services import DeviceService

router = APIRouter(
    prefix="/devices",
    tags=["devices"],
    responses={404: {"description": "Not found"}},
)


@router.post("/register", response_model=Device)
def register_device(device: Device, deviceService: DeviceService = Depends()):
    """
    Registers a new device with the push notification framework.

    Args:
        device (Device): The device to register.
        deviceService (DeviceService): An instance of the DeviceService class. Injected by FastAPI.

    Returns:
        Device: The registered device.
    """
    return deviceService.register_device(device)


@router.get("/all", response_model=list[Device])
def get_registered_devices(
    deviceService: DeviceService = Depends(),
):
    """
    Retrieve a list of all registered devices.

    Args:
        deviceService (DeviceService): An instance of the DeviceService class. Injected by FastAPI.

    Returns:
        list[Device]: A list of Device objects representing all registered devices.
    """
    return deviceService.get_registered_devices()


# FOR TESTING PURPOSES ONLY
@router.get("/clear", response_model=None)
def clear_registered_devices(
    deviceService: DeviceService = Depends(),
):
    """
    Clears all registered devices from the device service.
    """
    return deviceService.clear_registered_devices()
