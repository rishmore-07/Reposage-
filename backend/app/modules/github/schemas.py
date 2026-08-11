from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GitHubRepository(BaseModel):
    """
    Metadata for a GitHub repository fetched from the API.
    Only includes fields relevant to RepoSage.
    """
    model_config = ConfigDict(extra="ignore")

    id: int = Field(..., alias="id")
    name: str = Field(...)
    full_name: str = Field(...)
    description: str | None = None
    private: bool = Field(...)
    html_url: str = Field(...)
    clone_url: str = Field(...)
    ssh_url: str = Field(...)
    default_branch: str | None = Field(default="main")
    language: str | None = None
    stargazers_count: int = Field(default=0)
    forks_count: int = Field(default=0)
    updated_at: str | None = None

    # Owner details (nested in GitHub API)
    class Owner(BaseModel):
        model_config = ConfigDict(extra="ignore")
        login: str
        id: int
        avatar_url: str

    owner: Owner = Field(...)


class GitHubRepositoryListResponse(BaseModel):
    """
    Response wrapping a paginated list of GitHub repositories.
    """
    total_count: int | None = None
    has_next: bool = False
    items: list[GitHubRepository]
    page: int
    per_page: int
