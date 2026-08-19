import collections
import json
import logging
from collections.abc import Iterable
from enum import Enum

import httpx

from .credentials import CertificateCredentials, Credentials, TokenCredentials
from .errors import exception_class_for_reason
from .payload import Payload


class NotificationPriority(Enum):
    Immediate = "10"
    Delayed = "5"


class NotificationType(Enum):
    Alert = "alert"
    Background = "background"
    VoIP = "voip"
    Complication = "complication"
    FileProvider = "fileprovider"
    MDM = "mdm"


Notification = collections.namedtuple("Notification", ["token", "payload"])

DEFAULT_APNS_PRIORITY = NotificationPriority.Immediate

logger = logging.getLogger(__name__)


class APNsClient:
    SANDBOX_SERVER = "api.development.push.apple.com"
    LIVE_SERVER = "api.push.apple.com"

    DEFAULT_PORT = 443
    ALTERNATIVE_PORT = 2197

    def __init__(
        self,
        credentials: Credentials | str,
        use_sandbox: bool = False,
        use_alternative_port: bool = False,
        proto: str | None = None,
        json_encoder: type | None = None,
        password: str | None = None,
        proxy_host: str | None = None,
        proxy_port: int | None = None,
        heartbeat_period: float | None = None,
    ) -> None:
        if isinstance(credentials, str):
            self.__credentials = CertificateCredentials(credentials, password)
        else:
            self.__credentials = credentials

        self._init_connection(
            use_sandbox, use_alternative_port, proto, proxy_host, proxy_port
        )

        if heartbeat_period:
            raise NotImplementedError("heartbeat not supported")

        self.__json_encoder = json_encoder

        # APNs expects providers to keep connections open across requests;
        # opening one per notification is treated as abusive by Apple.
        ssl_context = self.__credentials.ssl_context
        self.__http_client = httpx.Client(
            http2=True, verify=ssl_context if ssl_context else True
        )

    def _init_connection(
        self,
        use_sandbox: bool,
        use_alternative_port: bool,
        proto: str | None,
        proxy_host: str | None,
        proxy_port: int | None,
    ) -> None:
        self.__server = self.SANDBOX_SERVER if use_sandbox else self.LIVE_SERVER
        self.__port = (
            self.ALTERNATIVE_PORT if use_alternative_port else self.DEFAULT_PORT
        )

    def send_notification(
        self,
        token_hex: str,
        notification: Payload,
        topic: str | None = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: int | None = None,
        collapse_id: str | None = None,
    ) -> None:
        status, reason = self.send_notification_sync(
            token_hex,
            notification,
            self.__http_client,
            topic,
            priority,
            expiration,
            collapse_id,
        )

        if status != 200:
            raise exception_class_for_reason(reason)(reason)

    def send_notification_sync(
        self,
        token_hex: str,
        notification: Payload,
        client: httpx.Client,
        topic: str | None = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: int | None = None,
        collapse_id: str | None = None,
        push_type: NotificationType | None = None,
    ) -> tuple[int, str]:
        json_str = json.dumps(
            notification.dict(),
            cls=self.__json_encoder,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        json_payload = json_str.encode("utf-8")

        headers = {}

        inferred_push_type = None  # type: Optional[str]
        if topic is not None:
            headers["apns-topic"] = topic
            if topic.endswith(".voip"):
                inferred_push_type = NotificationType.VoIP.value
            elif topic.endswith(".complication"):
                inferred_push_type = NotificationType.Complication.value
            elif topic.endswith(".pushkit.fileprovider"):
                inferred_push_type = NotificationType.FileProvider.value
            elif any(
                [
                    notification.alert is not None,
                    notification.badge is not None,
                    notification.sound is not None,
                ]
            ):
                inferred_push_type = NotificationType.Alert.value
            else:
                inferred_push_type = NotificationType.Background.value

        if push_type:
            inferred_push_type = push_type.value

        if inferred_push_type:
            headers["apns-push-type"] = inferred_push_type

        if priority != DEFAULT_APNS_PRIORITY:
            headers["apns-priority"] = priority.value

        if expiration is not None:
            headers["apns-expiration"] = "%d" % expiration

        if isinstance(self.__credentials, TokenCredentials):
            auth_header = self.__credentials.get_authorization_header(topic)
            if auth_header is not None:
                headers["authorization"] = auth_header

        if collapse_id is not None:
            headers["apns-collapse-id"] = collapse_id

        url = f"https://{self.__server}:{self.__port}/3/device/{token_hex}"
        response = client.post(url, headers=headers, content=json_payload)
        return response.status_code, self._extract_reason(response)

    @staticmethod
    def _extract_reason(response: httpx.Response) -> str:
        """Extract the 'reason' field from an APNs error response body.

        Bodies without a parseable reason (e.g. from an intermediary proxy) are
        never returned verbatim: a 410 is always Unregistered per the APNs spec,
        and anything else is reduced to a generic status marker.
        """
        if response.status_code == 200:
            return ""
        try:
            return response.json()["reason"]
        except (ValueError, KeyError, TypeError):
            logger.warning(
                "Unparseable APNs response body (status %d): %s",
                response.status_code,
                response.text[:200],
            )
            if response.status_code == 410:
                return "Unregistered"
            return f"HTTPError{response.status_code}"

    def get_notification_result(self, status: int, reason: str) -> str:
        """
        Get result for specified stream
        The function returns: 'Success' or 'failure reason'
        """
        if status == 200:
            return "Success"
        else:
            return reason

    def send_notification_batch(
        self,
        notifications: Iterable[Notification],
        topic: str | None = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: int | None = None,
        collapse_id: str | None = None,
        push_type: NotificationType | None = None,
    ) -> dict[str, str]:
        """
        Send a notification to a list of tokens in batch.

        The function returns a dictionary mapping each token to its result. The result is "Success"
        if the token was sent successfully, or the string returned by APNs in the 'reason' field of
        the response, if the token generated an error.
        """
        results = {}

        for next_notification in notifications:
            logger.info("Sending to token %s", next_notification.token)
            try:
                status, reason = self.send_notification_sync(
                    next_notification.token,
                    next_notification.payload,
                    self.__http_client,
                    topic,
                    priority,
                    expiration,
                    collapse_id,
                    push_type,
                )
            except httpx.HTTPError as error:
                logger.warning(
                    "Network error sending to token %s: %r",
                    next_notification.token,
                    error,
                )
                results[next_notification.token] = "ConnectionFailed"
                continue
            result = self.get_notification_result(status, reason)
            logger.info("Got response for %s: %s", next_notification.token, result)
            results[next_notification.token] = result

        return results

    def close(self) -> None:
        """Close the underlying HTTP connection to APNs."""
        self.__http_client.close()
