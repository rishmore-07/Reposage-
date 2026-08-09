"""
app/schemas/user.py

Pydantic v2 schemas for user-related endpoints.

Key design: UserRead never includes hashed_password.
The ORM model has the password field; the schema is the safe projection.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRead(BaseModel):
    """
    Schema returned by the API when exposing user data.
    Never includes hashed_password or any sensitive internal field.
    """

    model_config = {"from_attributes": True}  # Allow ORM model → schema conversion

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    avatar_url: str | None
    github_username: str | None
    is_active: bool
    is_email_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Request body for PATCH /api/v1/users/me — all fields optional."""

    full_name: str | None = Field(None, max_length=255, description="Display name")
    avatar_url: str | None = Field(None, max_length=2048, description="Profile picture URL")


class UserCreate(BaseModel):
    """
    Internal schema for creating a user record.
    Used by services — NOT exposed as an API endpoint directly
    (registration uses RegisterRequest → service → UserCreate).
    """

    email: EmailStr
    full_name: str | None = None
    hashed_password: str | None = None
    github_id: int | None = None
    github_username: str | None = None
    is_email_verified: bool = False
