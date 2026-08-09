"""
app/api/v1/users/router.py

User endpoints:
- GET /api/v1/users/me
- PATCH /api/v1/users/me
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import UserRead, UserUpdate

router = APIRouter()


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current user profile",
    description="Returns the profile of the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserRead,
    summary="Update current user profile",
    description="Updates the profile fields for the currently authenticated user.",
)
async def update_me(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserRead:
    repo = UserRepository(db)
    update_fields = update_data.model_dump(exclude_none=True)
    updated_user = await repo.update(current_user, **update_fields)
    return UserRead.model_validate(updated_user)
