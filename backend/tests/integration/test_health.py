"""
tests/integration/test_health.py

Integration test for the /health endpoint.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: AsyncClient) -> None:
    """Health endpoint should return 200 with status field."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "database" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_response_structure(client: AsyncClient) -> None:
    """Health response should match the HealthResponse schema."""
    response = await client.get("/health")
    data = response.json()
    assert data["status"] in ("ok", "degraded", "down")
    assert isinstance(data["version"], str)
    assert data["environment"] in ("development", "staging", "production")
