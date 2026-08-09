import httpx
from fastapi import HTTPException

from app.core.logging import get_logger
from app.modules.github.schemas import GitHubRepository

logger = get_logger(__name__)

GITHUB_API_URL = "https://api.github.com"


class GitHubClient:
    """
    Authenticated client for interacting with the GitHub REST API.
    """

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def get_user_repositories(
        self, query: str | None = None, page: int = 1, per_page: int = 20
    ) -> tuple[int | None, bool, list[GitHubRepository]]:
        """
        Fetches repositories accessible to the user.
        If `query` is provided, uses the search API restricted to the user.
        Otherwise, lists all repositories for the authenticated user.
        
        Returns a tuple of (total_count, has_next, repositories).
        """
        async with httpx.AsyncClient() as client:
            try:
                if query:
                    # Use search API restricted to user
                    search_query = f"{query} in:name,description"
                    response = await client.get(
                        f"{GITHUB_API_URL}/search/repositories",
                        headers=self.headers,
                        params={"q": search_query, "page": page, "per_page": per_page},
                    )
                else:
                    # Use standard user repos API
                    response = await client.get(
                        f"{GITHUB_API_URL}/user/repos",
                        headers=self.headers,
                        params={"type": "all", "sort": "updated", "page": page, "per_page": per_page},
                    )
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="GitHub API timed out.")
            except httpx.RequestError as e:
                logger.error(f"GitHub API request error: {e}")
                raise HTTPException(status_code=502, detail="Failed to connect to GitHub API.")

            self._handle_response_error(response, "fetch_repositories_failed")

            data = response.json()
            has_next = 'rel="next"' in response.headers.get("link", "")

            if query:
                # Search API returns { "total_count": int, "items": [...] }
                total_count = data.get("total_count")
                items = [GitHubRepository.model_validate(repo) for repo in data.get("items", [])]
                return total_count, has_next, items
            else:
                # User repos API returns a list directly.
                items = [GitHubRepository.model_validate(repo) for repo in data]
                return None, has_next, items

    async def get_repository(self, github_repo_id: int) -> GitHubRepository:
        """
        Fetches a specific repository by its GitHub ID.
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{GITHUB_API_URL}/repositories/{github_repo_id}",
                    headers=self.headers,
                )
            except httpx.TimeoutException:
                raise HTTPException(status_code=504, detail="GitHub API timed out.") from None
            except httpx.RequestError as e:
                logger.error(f"GitHub API request error: {e}")
                raise HTTPException(status_code=502, detail="Failed to connect to GitHub API.") from e

            self._handle_response_error(response, "fetch_repository_failed")
            return GitHubRepository.model_validate(response.json())

    def _handle_response_error(self, response: httpx.Response, action: str) -> None:
        """Raises a standardized HTTPException on GitHub API errors."""
        if response.status_code == 200:
            return

        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="GitHub token is invalid or expired.")
        if response.status_code == 403:
            # Check for rate limiting
            if "X-RateLimit-Remaining" in response.headers and response.headers["X-RateLimit-Remaining"] == "0":
                logger.warning(f"github_rate_limit_exceeded action={action}")
                raise HTTPException(status_code=429, detail="GitHub API rate limit exceeded.")
            raise HTTPException(status_code=403, detail="Access forbidden by GitHub.")
        if response.status_code == 404:
            raise HTTPException(status_code=404, detail="Repository not found on GitHub or you do not have access.")

        logger.error(f"{action} status={response.status_code} body={response.text}")
        raise HTTPException(status_code=502, detail="Failed to communicate with GitHub API.")
