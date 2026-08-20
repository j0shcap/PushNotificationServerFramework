from fastapi import APIRouter, Depends

from auth import require_api_key
from models import Device, DeviceRegistration
from services import DeviceService

# Registration is called by the iOS app itself and stays unauthenticated;
# everything that exposes or destroys device data goes on protected_router,
# so new routes are authenticated unless deliberately placed here.
router = APIRouter(
    prefix="/devices",
    tags=["devices"],
    responses={404: {"description": "Not found"}},
)

protected_router = APIRouter(
    prefix="/devices",
    tags=["devices"],
    dependencies=[Depends(require_api_key)],
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


@protected_router.get("/all", response_model=list[Device])
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


@protected_router.delete("", response_model=None)
def clear_registered_devices(
    device_service: DeviceService = Depends(),
):
    """
    Deletes all registered devices.
    """
    return device_service.clear_registered_devices()
