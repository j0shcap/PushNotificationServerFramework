from utils import getenv, getenv_bool

from .apn_handler import CertificateCredentials, Credentials, TokenCredentials


class PushConfig:
    """
    Reads push notification configuration from the environment.

    Token-based authentication with an APNs .p8 key is the default and
    Apple's recommended mechanism (keys do not expire). Setting
    APNS_CERT_PATH switches to certificate authentication using a PEM file
    containing the provider certificate and its private key.
    """

    @classmethod
    def get_apns_app_bundle_id(cls) -> str:
        """
        Returns the bundle ID pushes are addressed to (the apns-topic header).
        """
        return getenv("APNS_APP_BUNDLE_ID")

    @classmethod
    def get_use_sandbox(cls) -> bool:
        """
        Returns whether to target the APNs sandbox environment.

        Controlled by the APNS_USE_SANDBOX environment variable; defaults to False.
        Development builds get sandbox tokens, which the production server rejects.

        Raises:
            ValueError: If the variable is set to an unrecognized value, rather
                than silently falling back to the production environment.
        """
        return getenv_bool("APNS_USE_SANDBOX")

    @classmethod
    def get_credentials(cls) -> Credentials:
        """
        Builds APNs credentials from the environment.

        Returns:
            CertificateCredentials when APNS_CERT_PATH is set (with the
            passphrase from APNS_CERT_PASSWORD, if any); TokenCredentials
            built from APNS_AUTH_KEY_PATH, APNS_KEY_ID, and APNS_TEAM_ID
            otherwise.
        """
        cert_path = getenv("APNS_CERT_PATH", "")
        if cert_path:
            return CertificateCredentials(cert_path, password=getenv("APNS_CERT_PASSWORD", None))
        return TokenCredentials(
            auth_key_path=getenv("APNS_AUTH_KEY_PATH"),
            auth_key_id=getenv("APNS_KEY_ID"),
            team_id=getenv("APNS_TEAM_ID"),
        )
