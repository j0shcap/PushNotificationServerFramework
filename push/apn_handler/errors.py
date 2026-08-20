class APNsException(Exception):
    pass


class ConnectionFailed(APNsException):
    """There was an error connecting to APNs."""


class InternalException(APNsException):
    """This exception should not be raised. If it is, please report this as a bug."""


class BadPayloadException(APNsException):
    """Something bad with the payload."""


class BadCollapseId(BadPayloadException):
    """The collapse identifier exceeds the maximum allowed size"""


class BadDeviceToken(APNsException):
    """The specified device token was bad.
    Verify that the request contains a valid token and that the token matches the environment.
    """


class BadExpirationDate(BadPayloadException):
    """The apns-expiration value is bad."""


class BadMessageId(InternalException):
    """The apns-id value is bad."""


class BadPriority(InternalException):
    """The apns-priority value is bad."""


class BadTopic(BadPayloadException):
    """The apns-topic was invalid."""


class DeviceTokenNotForTopic(APNsException):
    """The device token does not match the specified topic."""


class DuplicateHeaders(InternalException):
    """One or more headers were repeated."""


class IdleTimeout(APNsException):
    """Idle time out."""


class MissingDeviceToken(APNsException):
    """The device token is not specified in the request :path.
    Verify that the :path header contains the device token."""


class MissingTopic(BadPayloadException):
    """The apns-topic header of the request was not specified and was required.
    The apns-topic header is mandatory when the client is connected using a certificate
    that supports multiple topics."""


class PayloadEmpty(BadPayloadException):
    """The message payload was empty."""


class TopicDisallowed(BadPayloadException):
    """Pushing to this topic is not allowed."""


class BadCertificate(APNsException):
    """The certificate was bad."""


class BadCertificateEnvironment(APNsException):
    """The client certificate was for the wrong environment."""


class ExpiredProviderToken(APNsException):
    """The provider token is stale and a new token should be generated."""


class Forbidden(APNsException):
    """The specified action is not allowed."""


class InvalidProviderToken(APNsException):
    """The provider token is not valid or the token signature could not be verified."""


class MissingProviderToken(APNsException):
    """No provider certificate was used to connect to APNs and Authorization
    header was missing or no provider token was specified."""


class BadPath(APNsException):
    """The request contained a bad :path value."""


class MethodNotAllowed(InternalException):
    """The specified :method was not POST."""


class Unregistered(APNsException):
    """The device token is inactive for the specified topic."""

    def __init__(self, *args, timestamp: str | None = None) -> None:
        super().__init__(*args)

        self.timestamp = timestamp


class ExpiredToken(APNsException):
    """The device token has expired."""

    def __init__(self, *args, timestamp: str | None = None) -> None:
        super().__init__(*args)

        self.timestamp = timestamp


class InvalidPushType(BadPayloadException):
    """The apns-push-type value is invalid."""


class BadEnvironmentKeyIdInToken(APNsException):
    """The key ID in the provider token does not match the environment."""


class UnrelatedKeyIdInToken(APNsException):
    """The key ID in the provider token is not related to the key ID used in
    the first push of this connection."""


class PayloadTooLarge(BadPayloadException):
    """The message payload was too large. The maximum payload size is 4096 bytes."""


class TooManyProviderTokenUpdates(APNsException):
    """The provider token is being updated too often."""


class TooManyRequests(APNsException):
    """Too many requests were made consecutively to the same device token."""


class InternalServerError(APNsException):
    """An internal server error occurred."""


class ServiceUnavailable(APNsException):
    """The service is unavailable."""


class Shutdown(APNsException):
    """The server is shutting down."""


REASON_TO_EXCEPTION: dict[str, type[APNsException]] = {
    "BadCollapseId": BadCollapseId,
    "BadDeviceToken": BadDeviceToken,
    "BadExpirationDate": BadExpirationDate,
    "BadMessageId": BadMessageId,
    "BadPriority": BadPriority,
    "BadTopic": BadTopic,
    "DeviceTokenNotForTopic": DeviceTokenNotForTopic,
    "DuplicateHeaders": DuplicateHeaders,
    "IdleTimeout": IdleTimeout,
    "MissingDeviceToken": MissingDeviceToken,
    "MissingTopic": MissingTopic,
    "PayloadEmpty": PayloadEmpty,
    "TopicDisallowed": TopicDisallowed,
    "BadCertificate": BadCertificate,
    "BadCertificateEnvironment": BadCertificateEnvironment,
    "ExpiredProviderToken": ExpiredProviderToken,
    "Forbidden": Forbidden,
    "InvalidProviderToken": InvalidProviderToken,
    "MissingProviderToken": MissingProviderToken,
    "BadPath": BadPath,
    "MethodNotAllowed": MethodNotAllowed,
    "Unregistered": Unregistered,
    "ExpiredToken": ExpiredToken,
    "InvalidPushType": InvalidPushType,
    "BadEnvironmentKeyIdInToken": BadEnvironmentKeyIdInToken,
    "UnrelatedKeyIdInToken": UnrelatedKeyIdInToken,
    "PayloadTooLarge": PayloadTooLarge,
    "TooManyProviderTokenUpdates": TooManyProviderTokenUpdates,
    "TooManyRequests": TooManyRequests,
    "InternalServerError": InternalServerError,
    "ServiceUnavailable": ServiceUnavailable,
    "Shutdown": Shutdown,
}
"""Every error reason documented by Apple, mapped to its exception class."""


def exception_class_for_reason(reason: str) -> type[APNsException]:
    """Map an APNs 'reason' string to its exception class.

    Falls back to APNsException for reasons this module does not know about,
    so new reasons introduced by Apple do not break error handling.
    """
    return REASON_TO_EXCEPTION.get(reason, APNsException)
