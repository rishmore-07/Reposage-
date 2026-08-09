"""
app/schemas/auth.py

Pydantic v2 schemas for authentication endpoints.
"""
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, SecretStr


class LoginRequest(BaseModel):
    """Request body for POST /api/v1/auth/login"""

    email: EmailStr = Field(..., description="User's email address")
    password: SecretStr = Field(
        ...,
        min_length=8,
        description="User's password (not logged or stored in plain text)",
    )


class RegisterRequest(BaseModel):
    """Request body for POST /api/v1/auth/register"""

    email: EmailStr = Field(..., description="Email address for the new account")
    password: SecretStr = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password — min 8 characters",
    )
    full_name: str | None = Field(
        None,
        max_length=255,
        description="Optional display name",
    )


class TokenResponse(BaseModel):
    """Response containing a JWT token pair."""

    access_token: str = Field(..., description="Short-lived JWT access token")
    refresh_token: str = Field(..., description="Long-lived JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")


class RefreshTokenRequest(BaseModel):
    """Request body for POST /api/v1/auth/refresh"""

    refresh_token: str = Field(..., description="Valid refresh token to exchange")
