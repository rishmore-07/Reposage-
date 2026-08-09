"""
app/api/dependencies.py

Shared FastAPI dependency injectors.

These functions are used with FastAPI's Depends() mechanism to inject:
- Database sessions (per-request lifecycle)
- The currently authenticated user
- Service instances

Why dependencies instead of imports?
- Testable: swap implementations in tests without changing route code
- Explicit: every route declares what it needs
- Scoped: sessions are tied to request lifecycle automatically
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, AuthenticationError
from app.db.session import get_db_session
from app.modules.users.models import User
from app.modules.auth.service import AuthService


async def get_db(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency that provides the AsyncSession for the current request.
    The session is managed by get_db_session() in db/session.py.
    """
    yield session


async def get_auth_service(
    db: AsyncSession = Depends(get_db),
) -> AuthService:
    """Dependency that provides an AuthService bound to the request session."""
    return AuthService(session=db)


async def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """
    Dependency that extracts and validates the access token from cookies, returning the User.

    Raises HTTP 401 if:
    - No access_token cookie is present
    - The token is invalid, expired, or malformed
    - The user no longer exists or is deactivated
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "authentication_required",
                "message": "Authentication cookies were not provided.",
            },
        )

    try:
        return await auth_service.get_current_user_from_token(token)
    except AppError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.error_code, "message": exc.message},
        ) from exc


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency that requires the current user to be a superuser.

    Raises HTTP 403 if the user is not a superuser.
    Use on admin-only endpoints.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "permission_denied",
                "message": "This endpoint requires superuser privileges.",
            },
        )
    return current_user
