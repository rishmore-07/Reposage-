from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""

    items: list[T]
    total: int = Field(..., description="Total number of items across all pages")
    page: int = Field(..., description="Current page number (1-indexed)")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(..., description="Total number of pages")
