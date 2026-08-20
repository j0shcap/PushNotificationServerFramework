import logging

from fastapi import Depends
from sqlalchemy.exc import SQLAlchemyError

from models import Message
from push import PushHandler, get_push_handler

from .device_service import DeviceService

logger = logging.getLogger(__name__)


class PushService:
    """
    A service for sending push notifications.

    Attributes:
        handler (PushHandler): The handler used to send push notifications. Injected by FastAPI.
        device_service (DeviceService): Used to remove devices APNs reports as
            unregistered. Injected by FastAPI.

    Methods:
        send_push(message: Message) -> dict[str, str]: Sends a push notification.
    """

    def __init__(
        self,
        handler: PushHandler = Depends(get_push_handler),
        device_service: DeviceService = Depends(),
    ):
        """
        Initialize the PushService.

        Args:
            handler (PushHandler): The push notification handler to use. Injected by FastAPI.
            device_service (DeviceService): The device service to use. Injected by FastAPI.
        """
        self.handler = handler
        self.device_service = device_service

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
        stale_tokens = [
            token
            for token, result in results.items()
            if result in ("Unregistered", "ExpiredToken")
        ]
        if stale_tokens:
            # Pruning is best-effort cleanup; the notifications are already
            # sent, so a database failure here must not turn the completed
            # push into an apparent failure (a client retry would re-send).
            try:
                self.device_service.remove_devices(stale_tokens)
                logger.info("Removed unregistered device tokens: %s", stale_tokens)
            except SQLAlchemyError:
                logger.exception("Failed to remove unregistered device tokens: %s", stale_tokens)
        return results
