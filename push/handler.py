from .apn_handler import APNsClient, Notification, Payload, TokenCredentials
from .config import PushConfig


class PushHandler:
    """
    A wrapper class for sending push notifications using the Apple Push Notification service (APNs).

    Attributes:
        token_credentials (TokenCredentials): A dictionary containing the token credentials required to connect to APNs.
        connection (APNsClient): An instance of the APNsClient class used to establish a connection to APNs.

    Methods:
        send_push(to_device_token: str, body: str, sound: str = "default", badge: int = 1) -> None:
            Sends a push notification to a single device token.
        send_multiple_push(to_device_tokens: list[str], body: str, sound: str = "default", badge: int = 1) -> None:
            Sends a push notification to multiple device tokens.
    """

    def __init__(self):
        self.token_credentials: TokenCredentials = PushConfig.get_token_credentials()
        self.connection: APNsClient = APNsClient(
            credentials=self.token_credentials,
            use_sandbox=PushConfig.get_use_sandbox(),
        )

    def send_push(
        self, to_device_token: str, body: str, sound: str = "default", badge: int = 1
    ) -> None:
        """
        Sends a push notification to a single device token.

        Args:
            to_device_token (str): The device token of the device to send the push notification to.
            body (str): The message body of the push notification.
            sound (str, optional): The name of the sound to play when the push notification is received. Defaults to "default".
            badge (int, optional): The number to display as the badge of the app icon. Defaults to 1.
        """
        payload: Payload = Payload(alert=body, sound=sound, badge=badge)
        self.connection.send_notification(
            to_device_token, payload, topic=PushConfig.get_apns_app_bundle_id()
        )

    def send_multiple_push(
        self,
        to_device_tokens: list[str],
        body: str,
        sound: str = "default",
        badge: int = 1,
    ) -> dict[str, str]:
        """
        Sends a push notification to multiple device tokens.

        A failure for one token does not prevent delivery to the others.

        Args:
            to_device_tokens (list[str]): A list of device tokens to send the push notification to.
            body (str): The message body of the push notification.
            sound (str, optional): The name of the sound to play when the push notification is received. Defaults to "default".
            badge (int, optional): The number to display as the badge of the app icon. Defaults to 1.

        Returns:
            dict[str, str]: A mapping of each device token to "Success" or the
                APNs failure reason.
        """
        payload: Payload = Payload(alert=body, sound=sound, badge=badge)
        notifications = [
            Notification(token=token, payload=payload) for token in to_device_tokens
        ]
        return self.connection.send_notification_batch(
            notifications, topic=PushConfig.get_apns_app_bundle_id()
        )


_shared_handler: PushHandler | None = None


def get_push_handler() -> PushHandler:
    """
    Returns the shared PushHandler instance, creating it on first use.

    A single instance is kept for the process lifetime so the APNs connection
    and cached JWT are reused across requests. Apple throttles providers that
    open connections or mint tokens too frequently.
    """
    global _shared_handler
    if _shared_handler is None:
        _shared_handler = PushHandler()
    return _shared_handler
