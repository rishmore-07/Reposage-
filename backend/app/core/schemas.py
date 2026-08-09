from __future__ import annotations

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    """Generic response for endpoints that only return a status message."""
    message: str = Field(..., description="A human-readable success or status message")


class HealthResponse(BaseModel):
    """Response model for the /health endpoint."""
    status: str
    version: str
    environment: str
    database: str
