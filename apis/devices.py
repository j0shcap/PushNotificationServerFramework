from fastapi import APIRouter, Depends

from auth import require_api_key
from models import Device, DeviceRegistration
from services import DeviceService

router = APIRouter(
    prefix="/devices",
    tags=["devices"],
    responses={404: {"description": "Not found"}},
)


@router.post("/register", response_model=Device)
def register_device(registration: DeviceRegistration, device_service: DeviceService = Depends()):
    """
    Registers a new device with the push notification framework.

    Args:
        registration (DeviceRegistration): The device information to register.
        device_service (DeviceService): An instance of the DeviceService class. Injected by FastAPI.

    Returns:
        Device: The registered device.
    """
    return device_service.register_device(registration)


@router.get("/all", response_model=list[Device], dependencies=[Depends(require_api_key)])
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


@router.delete("", response_model=None, dependencies=[Depends(require_api_key)])
def clear_registered_devices(
    device_service: DeviceService = Depends(),
):
    """
    Deletes all registered devices.
    """
    return device_service.clear_registered_devices()
