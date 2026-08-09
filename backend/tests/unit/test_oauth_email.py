import pytest
import respx
from fastapi import HTTPException
from httpx import Response

from app.modules.auth.oauth import GITHUB_API_URL, get_github_user_profile


@pytest.mark.asyncio
@respx.mock
async def test_github_primary_verified_email():
    """Test 1: Primary verified email."""
    respx.get(f"{GITHUB_API_URL}/user").mock(
        return_value=Response(200, json={"id": 1, "login": "test"})
    )
    respx.get(f"{GITHUB_API_URL}/user/emails").mock(
        return_value=Response(
            200,
            json=[
                {"email": "primary@example.com", "primary": True, "verified": True},
                {"email": "other@example.com", "primary": False, "verified": False},
            ],
        )
    )

    profile = await get_github_user_profile("fake_token")
    assert profile["email"] == "primary@example.com"


@pytest.mark.asyncio
@respx.mock
async def test_github_primary_unverified_fallback():
    """Test 2: Primary unverified email but another verified email exists."""
    respx.get(f"{GITHUB_API_URL}/user").mock(
        return_value=Response(200, json={"id": 1, "login": "test"})
    )
    respx.get(f"{GITHUB_API_URL}/user/emails").mock(
        return_value=Response(
            200,
            json=[
                {"email": "unverified_primary@example.com", "primary": True, "verified": False},
                {"email": "verified_secondary@example.com", "primary": False, "verified": True},
            ],
        )
    )

    profile = await get_github_user_profile("fake_token")
    assert profile["email"] == "verified_secondary@example.com"


@pytest.mark.asyncio
@respx.mock
async def test_github_no_verified_email():
    """Test 3: No verified email."""
    respx.get(f"{GITHUB_API_URL}/user").mock(
        return_value=Response(200, json={"id": 1, "login": "test"})
    )
    respx.get(f"{GITHUB_API_URL}/user/emails").mock(
        return_value=Response(
            200,
            json=[
                {"email": "unverified_primary@example.com", "primary": True, "verified": False},
                {"email": "unverified_secondary@example.com", "primary": False, "verified": False},
            ],
        )
    )

    with pytest.raises(HTTPException) as exc:
        await get_github_user_profile("fake_token")

    assert exc.value.status_code == 400
    assert "not have a verified email" in exc.value.detail
