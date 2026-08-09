"""
app/core/security.py

JWT token creation/verification and password hashing utilities.
Centralizes all cryptographic operations — no other module should
import jose or passlib directly.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import InvalidTokenError
from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Password Hashing ──────────────────────────────────────────────────────────


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt. Returns the hashed string."""
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.
    Returns True if they match, False otherwise.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        # Invalid hash format or rounds
        return False


# ── JWT Token Creation ────────────────────────────────────────────────────────


def create_access_token(
    subject: str | UUID,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:      The token subject (typically a user ID).
        expires_delta: Override the default expiry. Defaults to settings value.
        extra_claims:  Additional claims to embed in the token payload.

    Returns:
        A signed JWT string.
    """
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(subject: str | UUID) -> str:
    """
    Create a signed JWT refresh token with a longer expiry.

    Refresh tokens are long-lived and used only to obtain new access tokens.
    They should be stored securely (httpOnly cookie) and rotated on use.
    """
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.refresh_token_expire_days)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }

    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


# ── JWT Token Verification ────────────────────────────────────────────────────


def decode_token(token: str, *, expected_type: str = "access") -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Args:
        token:         The JWT string to verify.
        expected_type: The expected token type claim ("access" or "refresh").

    Returns:
        The decoded payload dict.

    Raises:
        InvalidTokenError: If the token is expired, malformed, has a bad
                           signature, or has the wrong type claim.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except JWTError as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        raise InvalidTokenError("Token is invalid or has expired.") from exc

    if payload.get("type") != expected_type:
        raise InvalidTokenError(
            f"Expected token type '{expected_type}', got '{payload.get('type')}'."
        )

    return payload


def get_subject_from_token(token: str, *, expected_type: str = "access") -> str:
    """
    Decode a token and return its 'sub' claim as a string.

    Raises:
        InvalidTokenError: If decoding fails or 'sub' is missing.
    """
    payload = decode_token(token, expected_type=expected_type)
    subject = payload.get("sub")
    if not subject or not isinstance(subject, str):
        raise InvalidTokenError("Token is missing a valid subject claim.")
    return subject
