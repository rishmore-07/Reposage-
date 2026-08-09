"""
app/api/v1/auth/router.py

Authentication endpoints:
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout (client-side only — JWTs are stateless)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_auth_service, get_db
from app.modules.auth.schemas import LoginRequest, RegisterRequest
from app.core.schemas import MessageResponse
from app.modules.auth.service import AuthService

router = APIRouter()


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Creates a new user account and sets HttpOnly cookies.",
)
async def register(
    request: RegisterRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    tokens = await auth_service.register(request)
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return MessageResponse(message="Registration successful")


@router.post(
    "/login",
    response_model=MessageResponse,
    summary="Authenticate with email and password",
    description="Validates credentials and sets HttpOnly cookies.",
)
async def login(
    request: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    tokens = await auth_service.login(request)
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return MessageResponse(message="Login successful")


@router.post(
    "/refresh",
    response_model=MessageResponse,
    summary="Exchange a refresh token for a new token pair",
    description="Accepts a valid refresh token from cookies and returns a new token pair in cookies.",
)
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Refresh token missing")
        
    tokens = await auth_service.refresh_tokens(refresh_token)
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)
    return MessageResponse(message="Tokens refreshed")


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out the current session",
    description="Clears authentication cookies.",
)
async def logout(response: Response) -> MessageResponse:
    response.delete_cookie("access_token", path="/", httponly=True, samesite="lax")
    response.delete_cookie("refresh_token", path="/api/v1/auth/refresh", httponly=True, samesite="lax")
    return MessageResponse(message="Logged out successfully.")


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    from app.core.config import settings
    # Access token valid for all paths
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    # Refresh token only sent to the refresh endpoint for extra security
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/api/v1/auth/refresh",
    )
