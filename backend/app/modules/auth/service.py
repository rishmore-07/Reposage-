"""
app/services/auth_service.py

Authentication service: login, register, token refresh.

This service:
- Validates credentials and creates JWT tokens
- Never touches the DB directly — delegates to UserRepository
- Never imports from the API layer
- Is injected into routes via FastAPI Depends()
"""

from __future__ import annotations

from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_subject_from_token,
    hash_password,
    verify_password,
)
from app.modules.auth.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

logger = get_logger(__name__)


class AuthService:
    """Handles authentication and authorization operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def login(self, request: LoginRequest) -> TokenResponse:
        """
        Authenticate a user with email and password.

        Returns a JWT token pair on success.
        Raises InvalidCredentialsError on any authentication failure
        (intentionally vague to prevent user enumeration attacks).
        """
        user = await self.user_repo.get_by_email(request.email)

        # Timing-safe check: always verify password hash even if user doesn't exist
        # to prevent timing attacks that could reveal valid email addresses
        if user is None or not user.hashed_password:
            # Perform a dummy hash verification to maintain constant timing
            verify_password("dummy_check", "$2b$12$" + "a" * 53)
            raise InvalidCredentialsError()

        if not verify_password(request.password.get_secret_value(), user.hashed_password):
            logger.warning("login_failed", email=request.email)
            raise InvalidCredentialsError()

        if not user.is_active:
            raise InvalidCredentialsError("Account is deactivated.")

        logger.info("login_success", user_id=str(user.id), email=user.email)

        return TokenResponse(
            access_token=create_access_token(subject=user.id),
            refresh_token=create_refresh_token(subject=user.id),
        )

    async def register(self, request: RegisterRequest) -> TokenResponse:
        """
        Create a new user account and return a token pair.

        Raises EmailAlreadyExistsError if the email is taken.
        """
        if await self.user_repo.email_exists(request.email):
            raise EmailAlreadyExistsError()

        user = await self.user_repo.create(
            email=request.email.lower(),
            full_name=request.full_name,
            hashed_password=hash_password(request.password.get_secret_value()),
        )

        logger.info("user_registered", user_id=str(user.id), email=user.email)

        return TokenResponse(
            access_token=create_access_token(subject=user.id),
            refresh_token=create_refresh_token(subject=user.id),
        )

    async def refresh_tokens(self, refresh_token: str) -> TokenResponse:
        """
        Exchange a valid refresh token for a new token pair.

        The refresh token is validated and the user's existence is confirmed
        before issuing new tokens. This allows token revocation by deactivating
        the user account.
        """
        try:
            user_id = get_subject_from_token(refresh_token, expected_type="refresh")
        except InvalidTokenError:
            raise

        user = await self.user_repo.get_by_id_str(user_id)
        if user is None or not user.is_active:
            raise InvalidTokenError("Token belongs to an invalid or inactive user.")

        logger.info("tokens_refreshed", user_id=str(user.id))

        return TokenResponse(
            access_token=create_access_token(subject=user.id),
            refresh_token=create_refresh_token(subject=user.id),
        )

    async def get_current_user_from_token(self, token: str) -> User:
        """
        Validate an access token and return the associated User.

        Used by the authentication dependency in api/dependencies.py.
        """
        import uuid

        from app.core.exceptions import AuthenticationError

        user_id_str = get_subject_from_token(token, expected_type="access")

        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError as exc:
            raise InvalidTokenError("Token subject is not a valid UUID.") from exc

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User associated with this token no longer exists.")

        if not user.is_active:
            raise AuthenticationError("User account is deactivated.")

        return user

    async def login_or_register_github(
        self, github_profile: dict, access_token: str
    ) -> TokenResponse:
        """
        Authenticate a user with their GitHub profile, creating an account if necessary.
        """
        from datetime import datetime

        from app.core.encryption import encrypt_string

        github_id = github_profile.get("id")
        email = github_profile.get("email")

        if not github_id or not email:
            raise InvalidCredentialsError("Incomplete GitHub profile data.")

        from sqlalchemy import select

        # Look up exclusively by github_id to prevent account takeover via email match
        user = await self.user_repo.session.scalar(select(User).filter(User.github_id == github_id))

        if not user:
            # If the email is already in use by another account, we must NOT automatically link them.
            # Doing so would allow an email-match account takeover if GitHub didn't verify the email properly,
            # or it simply violates the principle of explicit intent.
            existing_email_user = await self.user_repo.get_by_email(email)
            if existing_email_user:
                raise EmailAlreadyExistsError(
                    "An account with this email already exists. Please log in using your password to link your GitHub account."
                )

        encrypted_token = encrypt_string(access_token)
        now = datetime.now(UTC)

        if user:
            # Update existing user with GitHub info and token
            user = await self.user_repo.update(
                user,
                github_id=github_id,
                github_username=github_profile.get("login"),
                github_access_token=encrypted_token,
                last_login_at=now,
                avatar_url=github_profile.get("avatar_url") or user.avatar_url,
                full_name=github_profile.get("name") or user.full_name,
            )
        else:
            # Create new user
            user = await self.user_repo.create(
                email=email,
                full_name=github_profile.get("name"),
            )
            # update the rest which are not in UserCreate
            user = await self.user_repo.update(
                user,
                github_id=github_id,
                github_username=github_profile.get("login"),
                github_access_token=encrypted_token,
                last_login_at=now,
                avatar_url=github_profile.get("avatar_url"),
                is_email_verified=True,
            )

        logger.info("github_login_success", user_id=str(user.id), email=user.email)

        return TokenResponse(
            access_token=create_access_token(subject=user.id),
            refresh_token=create_refresh_token(subject=user.id),
        )
