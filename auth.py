"""API key authentication for protected endpoints."""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from utils import getenv

_bearer_scheme = HTTPBearer(auto_error=False)


def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> None:
    """
    FastAPI dependency that rejects requests without a valid API key.

    Clients authenticate with an `Authorization: Bearer <API_KEY>` header.
    The comparison is constant-time to avoid leaking key material through
    response-timing differences.

    Raises:
        HTTPException: 401 if the header is missing or the key does not match.
    """
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), getenv("API_KEY", "").encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
