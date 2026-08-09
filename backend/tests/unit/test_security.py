"""
tests/unit/test_security.py

Unit tests for app/core/security.py.

These tests verify:
- Password hashing and verification
- JWT token creation and decoding
- Token type validation (prevents access tokens used as refresh tokens)
- Expired token handling
"""
from __future__ import annotations

import uuid
from datetime import timedelta

import pytest

from app.core.exceptions import InvalidTokenError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_subject_from_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    """Tests for bcrypt password hashing."""

    def test_hash_password_returns_string(self) -> None:
        result = hash_password("my-secret-password")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_is_not_plaintext(self) -> None:
        plain = "my-secret-password"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_verify_correct_password(self) -> None:
        plain = "correct-horse-battery-staple"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password(self) -> None:
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_same_password_different_hashes(self) -> None:
        """bcrypt generates a unique salt each time."""
        plain = "same-password"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert hash1 != hash2
        assert verify_password(plain, hash1) is True
        assert verify_password(plain, hash2) is True


class TestJWTTokens:
    """Tests for JWT token creation and verification."""

    def test_create_access_token_is_string(self) -> None:
        token = create_access_token(subject=uuid.uuid4())
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token(self) -> None:
        subject = uuid.uuid4()
        token = create_access_token(subject=subject)
        payload = decode_token(token, expected_type="access")
        assert payload["sub"] == str(subject)
        assert payload["type"] == "access"

    def test_decode_refresh_token(self) -> None:
        subject = uuid.uuid4()
        token = create_refresh_token(subject=subject)
        payload = decode_token(token, expected_type="refresh")
        assert payload["sub"] == str(subject)
        assert payload["type"] == "refresh"

    def test_access_token_rejected_as_refresh(self) -> None:
        """Access tokens must not be accepted where refresh tokens are expected."""
        token = create_access_token(subject=uuid.uuid4())
        with pytest.raises(InvalidTokenError):
            decode_token(token, expected_type="refresh")

    def test_refresh_token_rejected_as_access(self) -> None:
        """Refresh tokens must not be accepted where access tokens are expected."""
        token = create_refresh_token(subject=uuid.uuid4())
        with pytest.raises(InvalidTokenError):
            decode_token(token, expected_type="access")

    def test_expired_token_raises_error(self) -> None:
        """Tokens with a past expiry must be rejected."""
        token = create_access_token(
            subject=uuid.uuid4(),
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        with pytest.raises(InvalidTokenError):
            decode_token(token)

    def test_tampered_token_raises_error(self) -> None:
        """Tokens with a modified signature must be rejected."""
        token = create_access_token(subject=uuid.uuid4())
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(InvalidTokenError):
            decode_token(tampered)

    def test_get_subject_from_token(self) -> None:
        subject = uuid.uuid4()
        token = create_access_token(subject=subject)
        result = get_subject_from_token(token)
        assert result == str(subject)
