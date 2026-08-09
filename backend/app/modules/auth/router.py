"""
app/api/v1/auth/router.py

Authentication endpoints:
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- POST /api/v1/auth/logout (client-side only — JWTs are stateless)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies import get_auth_service
from app.core.schemas import MessageResponse
from app.modules.auth.schemas import LoginRequest, RegisterRequest
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
    from app.core.config import settings

    response.delete_cookie(
        "access_token", path="/", httponly=True, secure=settings.is_production, samesite="lax"
    )
    response.delete_cookie(
        "refresh_token",
        path="/api/v1/auth/refresh",
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )
    return MessageResponse(message="Logged out successfully.")


@router.get(
    "/github/login",
    summary="Redirect to GitHub OAuth",
)
async def github_login(response: Response):
    import uuid

    from app.modules.auth.oauth import get_github_auth_url

    state = str(uuid.uuid4())
    url = get_github_auth_url(state)

    from fastapi.responses import RedirectResponse

    redirect = RedirectResponse(url)

    from app.core.config import settings

    # Store state in cookie to prevent CSRF
    redirect.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=settings.is_production,
        max_age=600,  # 10 minutes
        samesite="lax",
    )

    return redirect


@router.get(
    "/github/callback",
    summary="GitHub OAuth callback",
)
async def github_callback(
    request: Request,
    response: Response,
    code: str,
    state: str,
    auth_service: AuthService = Depends(get_auth_service),
):
    from fastapi import HTTPException
    from fastapi.responses import RedirectResponse

    from app.core.config import settings
    from app.modules.auth.oauth import exchange_code_for_token, get_github_user_profile

    # Verify state
    cookie_state = request.cookies.get("oauth_state")
    if not cookie_state or cookie_state != state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    # Exchange code for access token
    access_token = await exchange_code_for_token(code)

    # Get user profile
    github_profile = await get_github_user_profile(access_token)

    # Login or register
    tokens = await auth_service.login_or_register_github(github_profile, access_token)

    # Set cookies
    _set_auth_cookies(response, tokens.access_token, tokens.refresh_token)

    # Redirect to frontend
    frontend_url = "http://localhost:5173/dashboard"
    if settings.is_production:
        frontend_url = "/dashboard"  # In production, backend and frontend are on same origin

    redirect = RedirectResponse(frontend_url)
    # Important: RedirectResponse creates a new response object, so we must set cookies on it
    _set_auth_cookies(redirect, tokens.access_token, tokens.refresh_token)
    redirect.delete_cookie("oauth_state")

    return redirect


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
