import json
import logging
from collections.abc import Iterable
from enum import StrEnum
from typing import NamedTuple

import httpx

from .credentials import Credentials, TokenCredentials
from .errors import exception_class_for_reason
from .payload import Payload

DEFAULT_REQUEST_TIMEOUT = 10.0

logger = logging.getLogger(__name__)


class NotificationPriority(StrEnum):
    Immediate = "10"
    Delayed = "5"


class NotificationType(StrEnum):
    Alert = "alert"
    Background = "background"
    VoIP = "voip"
    Complication = "complication"
    FileProvider = "fileprovider"
    MDM = "mdm"
    LiveActivity = "liveactivity"
    Location = "location"
    Widgets = "widgets"
    Controls = "controls"
    PushToTalk = "pushtotalk"


class Notification(NamedTuple):
    token: str
    payload: Payload


DEFAULT_APNS_PRIORITY = NotificationPriority.Immediate

# apns-push-type values inferred from conventional apns-topic suffixes.
_PUSH_TYPE_BY_TOPIC_SUFFIX = {
    ".voip-ptt": NotificationType.PushToTalk,
    ".voip": NotificationType.VoIP,
    ".complication": NotificationType.Complication,
    ".pushkit.fileprovider": NotificationType.FileProvider,
    ".push-type.liveactivity": NotificationType.LiveActivity,
    ".location-query": NotificationType.Location,
    ".push-type.widgets": NotificationType.Widgets,
    ".push-type.controls": NotificationType.Controls,
}


class APNsClient:
    SANDBOX_SERVER = "api.sandbox.push.apple.com"
    LIVE_SERVER = "api.push.apple.com"

    DEFAULT_PORT = 443
    ALTERNATIVE_PORT = 2197

    def __init__(
        self,
        credentials: Credentials,
        use_sandbox: bool = False,
        use_alternative_port: bool = False,
        json_encoder: type | None = None,
    ) -> None:
        self._credentials = credentials
        self._json_encoder = json_encoder
        self._server = self.SANDBOX_SERVER if use_sandbox else self.LIVE_SERVER
        self._port = self.ALTERNATIVE_PORT if use_alternative_port else self.DEFAULT_PORT

        # APNs expects providers to keep connections open across requests;
        # opening one per notification is treated as abusive by Apple.
        ssl_context = credentials.ssl_context
        self._http_client = httpx.Client(
            http2=True,
            verify=ssl_context if ssl_context else True,
            timeout=DEFAULT_REQUEST_TIMEOUT,
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
        status, reason = self._send(
            token_hex,
            notification,
            topic,
            priority,
            expiration,
            collapse_id,
        )

        if status != 200:
            raise exception_class_for_reason(reason)(reason)

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
        Send a notification to a list of tokens.

        Returns a dictionary mapping each token to "Success", the reason
        string APNs answered with, or "ConnectionFailed" for a network error.
        A failure for one token does not prevent delivery to the others.
        """
        results = {}

        for notification in notifications:
            logger.info("Sending to token %s", notification.token)
            try:
                status, reason = self._send(
                    notification.token,
                    notification.payload,
                    topic,
                    priority,
                    expiration,
                    collapse_id,
                    push_type,
                )
            except httpx.HTTPError as error:
                logger.warning("Network error sending to token %s: %r", notification.token, error)
                results[notification.token] = "ConnectionFailed"
                continue
            result = "Success" if status == 200 else reason
            logger.info("Got response for %s: %s", notification.token, result)
            results[notification.token] = result

        return results

    def close(self) -> None:
        """Close the underlying HTTP connection to APNs."""
        self._http_client.close()

    def _send(
        self,
        token_hex: str,
        notification: Payload,
        topic: str | None = None,
        priority: NotificationPriority = NotificationPriority.Immediate,
        expiration: int | None = None,
        collapse_id: str | None = None,
        push_type: NotificationType | None = None,
    ) -> tuple[int, str]:
        json_str = json.dumps(
            notification.dict(),
            cls=self._json_encoder,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        json_payload = json_str.encode("utf-8")

        headers = {}

        if topic is not None:
            headers["apns-topic"] = topic

        if push_type is None:
            push_type = self._infer_push_type(topic, notification)
        if push_type is not None:
            headers["apns-push-type"] = push_type.value

        if priority != DEFAULT_APNS_PRIORITY:
            headers["apns-priority"] = priority.value

        if expiration is not None:
            headers["apns-expiration"] = str(expiration)

        if isinstance(self._credentials, TokenCredentials):
            headers["authorization"] = self._credentials.get_authorization_header()

        if collapse_id is not None:
            headers["apns-collapse-id"] = collapse_id

        url = f"https://{self._server}:{self._port}/3/device/{token_hex}"
        response = self._http_client.post(url, headers=headers, content=json_payload)
        return response.status_code, self._extract_reason(response)

    @staticmethod
    def _infer_push_type(topic: str | None, notification: Payload) -> NotificationType | None:
        if topic is None:
            return None
        for suffix, push_type in _PUSH_TYPE_BY_TOPIC_SUFFIX.items():
            if topic.endswith(suffix):
                return push_type
        if any(
            value is not None
            for value in (notification.alert, notification.badge, notification.sound)
        ):
            return NotificationType.Alert
        return NotificationType.Background

    @staticmethod
    def _extract_reason(response: httpx.Response) -> str:
        """Extract the 'reason' field from an APNs error response body.

        Bodies without a parseable reason (e.g. from an intermediary proxy) are
        never returned verbatim: per the APNs spec a 410 always means the token
        is gone, so it maps to Unregistered; anything else is reduced to a
        generic status marker.
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
