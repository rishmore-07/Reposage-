import urllib.parse

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


def get_github_auth_url(state: str) -> str:
    """Generates the GitHub OAuth authorization URL."""
    if not settings.github_client_id:
        raise HTTPException(status_code=500, detail="GitHub OAuth is not configured.")

    params = {
        "client_id": settings.github_client_id,
        "state": state,
        "scope": "read:user user:email repo",  # 'repo' scope for Phase 2
    }
    query_string = urllib.parse.urlencode(params)
    return f"{GITHUB_AUTH_URL}?{query_string}"


async def exchange_code_for_token(code: str) -> str:
    """Exchanges the authorization code for an access token."""
    if not settings.github_client_id or not settings.github_client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth is not configured.")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )

        if response.status_code != 200:
            logger.error(
                "github_token_exchange_failed", status=response.status_code, body=response.text
            )
            raise HTTPException(status_code=400, detail="Failed to exchange code for token.")

        data = response.json()
        if "error" in data:
            logger.error(
                "github_oauth_error",
                error=data.get("error"),
                description=data.get("error_description"),
            )
            raise HTTPException(
                status_code=400, detail=data.get("error_description", "OAuth error")
            )

        return data["access_token"]


async def get_github_user_profile(access_token: str) -> dict:
    """Fetches the user's GitHub profile and primary email."""
    async with httpx.AsyncClient() as client:
        # Get profile
        profile_response = await client.get(
            f"{GITHUB_API_URL}/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if profile_response.status_code != 200:
            logger.error("github_profile_failed", status=profile_response.status_code)
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub profile.")

        profile = profile_response.json()

        # Get emails
        emails_response = await client.get(
            f"{GITHUB_API_URL}/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

        if emails_response.status_code == 200:
            emails = emails_response.json()

            # Prefer primary verified email
            primary_verified = next(
                (e["email"] for e in emails if e.get("primary") and e.get("verified")), None
            )

            # Fallback to any verified email
            any_verified = next((e["email"] for e in emails if e.get("verified")), None)

            # Assign in order of preference
            verified_email = primary_verified or any_verified
            if verified_email:
                profile["email"] = verified_email
            else:
                profile["email"] = None

        if not profile.get("email"):
            raise HTTPException(
                status_code=400,
                detail="GitHub account does not have a verified email address. Please verify your email on GitHub.",
            )

        return profile
