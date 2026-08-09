from app.core.encryption import decrypt_string
from app.modules.github.client import GitHubClient
from app.modules.github.schemas import GitHubRepository, GitHubRepositoryListResponse
from app.modules.users.models import User


class GitHubService:
    """
    Business logic layer for interacting with GitHub on behalf of a user.
    Handles token decryption safely without exposing tokens to upper layers.
    """

    def __init__(self, user: User) -> None:
        self.user = user
        if not user.github_access_token:
            raise ValueError("User does not have a GitHub access token connected.")

        token = decrypt_string(user.github_access_token)
        self.client = GitHubClient(access_token=token)

    async def get_available_repositories(
        self, query: str | None = None, page: int = 1, per_page: int = 20
    ) -> GitHubRepositoryListResponse:
        """
        Retrieves repositories the user can connect to.
        """
        total_count, has_next, items = await self.client.get_user_repositories(
            query=query, page=page, per_page=per_page
        )

        return GitHubRepositoryListResponse(
            total_count=total_count,
            has_next=has_next,
            items=items,
            page=page,
            per_page=per_page,
        )

    async def get_repository_metadata(self, github_repo_id: int) -> GitHubRepository:
        """
        Retrieves and validates metadata for a specific repository.
        By using the authenticated client, this inherently verifies that the
        user has access to the repository on GitHub.
        """
        return await self.client.get_repository(github_repo_id)
