import ssl
import time

import jwt

DEFAULT_TOKEN_LIFETIME = 2700
DEFAULT_TOKEN_ENCRYPTION_ALGORITHM = "ES256"


class Credentials:
    """Base class for APNs credentials. Not instantiated directly."""

    def __init__(self, ssl_context: ssl.SSLContext | None = None) -> None:
        self.ssl_context = ssl_context

    def get_authorization_header(self) -> str | None:
        return None


class CertificateCredentials(Credentials):
    """Certificate-based authentication: the client certificate is presented
    during the TLS handshake, so no authorization header is sent."""

    def __init__(self, cert_file: str, password: str | None = None) -> None:
        ssl_context = ssl.create_default_context()
        ssl_context.load_cert_chain(cert_file, password=password)
        super().__init__(ssl_context)


class TokenCredentials(Credentials):
    """JWT token-based authentication using an APNs .p8 signing key.

    Tokens are cached and reused until they near Apple's one-hour validity
    limit; Apple throttles providers that mint tokens more than once every
    20 minutes.
    """

    def __init__(
        self,
        auth_key_path: str,
        auth_key_id: str,
        team_id: str,
        encryption_algorithm: str = DEFAULT_TOKEN_ENCRYPTION_ALGORITHM,
        token_lifetime: int = DEFAULT_TOKEN_LIFETIME,
    ) -> None:
        with open(auth_key_path) as key_file:
            self._auth_key = key_file.read()
        self._auth_key_id = auth_key_id
        self._team_id = team_id
        self._encryption_algorithm = encryption_algorithm
        self._token_lifetime = token_lifetime
        self._cached_token: tuple[float, str] | None = None

        super().__init__()

    def get_authorization_header(self) -> str:
        return f"bearer {self._get_or_create_token()}"

    def _get_or_create_token(self) -> str:
        if self._cached_token is not None:
            issued_at, token = self._cached_token
            if time.time() <= issued_at + self._token_lifetime:
                return token

        issued_at = time.time()
        token = jwt.encode(
            {"iss": self._team_id, "iat": issued_at},
            self._auth_key,
            algorithm=self._encryption_algorithm,
            headers={"alg": self._encryption_algorithm, "kid": self._auth_key_id},
        )
        self._cached_token = (issued_at, token)
        return token
