from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_string
from app.modules.users.models import User


@pytest.fixture
def mock_github_profile():
    return {
        "id": 123456,
        "login": "testuser",
        "email": "test@example.com",
        "name": "Test User",
        "avatar_url": "https://github.com/avatar.png",
    }


@pytest.mark.asyncio
async def test_oauth_login_redirect(client: AsyncClient):
    with patch("app.modules.auth.oauth.settings.github_client_id", "mock_client_id"):
        response = await client.get("/api/v1/auth/github/login", follow_redirects=False)
        assert response.status_code == 307
        assert "github.com/login/oauth/authorize" in response.headers["location"]

    # Check if state cookie was set
    cookies = response.cookies
    assert "oauth_state" in cookies
    assert len(cookies["oauth_state"]) > 0


@pytest.mark.asyncio
async def test_oauth_callback_invalid_state(client: AsyncClient):
    response = await client.get("/api/v1/auth/github/callback?code=123&state=invalid_state")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OAuth state."


@pytest.mark.asyncio
async def test_oauth_callback_new_user(
    client: AsyncClient, test_db_session: AsyncSession, mock_github_profile: dict
):
    with (
        patch("app.modules.auth.oauth.settings.github_client_id", "mock_client_id"),
        patch("app.modules.auth.oauth.settings.github_client_secret", "mock_client_secret"),
    ):
        # First get the state cookie
        login_response = await client.get("/api/v1/auth/github/login", follow_redirects=False)
        state = login_response.cookies.get("oauth_state")

        with (
            patch("app.modules.auth.oauth.exchange_code_for_token") as mock_exchange,
            patch("app.modules.auth.oauth.get_github_user_profile") as mock_profile,
        ):
            mock_exchange.return_value = "fake_access_token_123"
            mock_profile.return_value = mock_github_profile

            response = await client.get(
                f"/api/v1/auth/github/callback?code=mock_code&state={state}",
                cookies={"oauth_state": state},
                follow_redirects=False,
            )

        assert response.status_code == 307
        assert "dashboard" in response.headers["location"]
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies

        from sqlalchemy import select

        result = await test_db_session.execute(
            select(User).filter(User.email == mock_github_profile["email"])
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.github_id == mock_github_profile["id"]
        assert user.github_username == mock_github_profile["login"]
        assert user.full_name == mock_github_profile["name"]

        # Verify encryption
        decrypted_token = decrypt_string(user.github_access_token)
        assert decrypted_token == "fake_access_token_123"


@pytest.mark.asyncio
async def test_oauth_callback_existing_email_fails_linking(
    client: AsyncClient, test_db_session: AsyncSession, mock_github_profile: dict
):
    """Test 6: GitHub ID not matching but email matching an existing account."""
    from app.core.security import hash_password

    # Setup existing user with password but NO github_id
    user = User(
        email=mock_github_profile["email"],
        hashed_password=hash_password("password123"),
        is_email_verified=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    with (
        patch("app.modules.auth.oauth.settings.github_client_id", "mock_client_id"),
        patch("app.modules.auth.oauth.settings.github_client_secret", "mock_client_secret"),
    ):
        login_response = await client.get("/api/v1/auth/github/login", follow_redirects=False)
        state = login_response.cookies.get("oauth_state")

        with (
            patch("app.modules.auth.oauth.exchange_code_for_token") as mock_exchange,
            patch("app.modules.auth.oauth.get_github_user_profile") as mock_profile,
        ):
            mock_exchange.return_value = "fake_access_token_456"
            mock_profile.return_value = mock_github_profile

            response = await client.get(
                f"/api/v1/auth/github/callback?code=mock_code&state={state}",
                cookies={"oauth_state": state},
                follow_redirects=False,
            )

        # Should fail with 409 Conflict because email exists but github_id doesn't match
        assert response.status_code == 409
        assert "email already exists" in response.json()["message"]


@pytest.mark.asyncio
async def test_oauth_callback_existing_github_id_success(
    client: AsyncClient, test_db_session: AsyncSession, mock_github_profile: dict
):
    """Test 5: GitHub ID matching an existing RepoSage user."""
    from sqlalchemy import select

    from app.core.security import hash_password

    # Setup existing user with matching github_id
    user = User(
        email="oldemail@example.com",  # Even if email differs, github_id matches!
        github_id=mock_github_profile["id"],
        hashed_password=hash_password("password123"),
        is_email_verified=True,
    )
    test_db_session.add(user)
    await test_db_session.commit()

    with (
        patch("app.modules.auth.oauth.settings.github_client_id", "mock_client_id"),
        patch("app.modules.auth.oauth.settings.github_client_secret", "mock_client_secret"),
    ):
        login_response = await client.get("/api/v1/auth/github/login", follow_redirects=False)
        state = login_response.cookies.get("oauth_state")

        with (
            patch("app.modules.auth.oauth.exchange_code_for_token") as mock_exchange,
            patch("app.modules.auth.oauth.get_github_user_profile") as mock_profile,
        ):
            mock_exchange.return_value = "fake_access_token_456"
            mock_profile.return_value = mock_github_profile

            response = await client.get(
                f"/api/v1/auth/github/callback?code=mock_code&state={state}",
                cookies={"oauth_state": state},
                follow_redirects=False,
            )

        assert response.status_code == 307

        result = await test_db_session.execute(
            select(User).filter(User.github_id == mock_github_profile["id"])
        )
        updated_user = result.scalar_one_or_none()
        assert updated_user is not None
        assert updated_user.github_id == mock_github_profile["id"]

        # Token updated
        assert decrypt_string(updated_user.github_access_token) == "fake_access_token_456"
