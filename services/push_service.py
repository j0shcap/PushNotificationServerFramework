from fastapi import Depends
from models import Message
from push import PushHandler, get_push_handler

from .device_service import DeviceService


class PushService:
    """
    A service for sending push notifications.

    Attributes:
        handler (PushHandler): The handler used to send push notifications. Injected by FastAPI.
        deviceService (DeviceService): Used to remove devices APNs reports as unregistered. Injected by FastAPI.

    Methods:
        send_push(message: Message) -> dict[str, str]: Sends a push notification.
    """

    def __init__(
        self,
        handler: PushHandler = Depends(get_push_handler),
        deviceService: DeviceService = Depends(),
    ):
        """
        Initialize the PushService.

        Args:
            handler (PushHandler): The push notification handler to use. Injected by FastAPI.
            deviceService (DeviceService): The device service to use. Injected by FastAPI.
        """
        self.handler = handler
        self.deviceService = deviceService

    def send_push(self, message: Message) -> dict[str, str]:
        """
        Send a push notification to each recipient.

        Recipients whose tokens APNs reports as unregistered are removed from
        the database, per Apple's guidance to stop pushing to stale tokens.

        Args:
            message (Message): The message to send.

        Returns:
            dict[str, str]: A mapping of each device token to "Success" or the
                APNs failure reason.
        """
        results = self.handler.send_multiple_push(
            to_device_tokens=message.recipients, body=message.body
        )
        for token, result in results.items():
            if result == "Unregistered":
                self.deviceService.remove_device(token)
        return results
