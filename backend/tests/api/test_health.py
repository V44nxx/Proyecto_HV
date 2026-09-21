"""
API tests for /health endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:

    @pytest.mark.asyncio
    async def test_health_returns_200(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_returns_ok_status(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_db_returns_200(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/health/db")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_response_has_request_id_header(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/health")
        assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    async def test_health_has_security_headers(self, api_client: AsyncClient) -> None:
        response = await api_client.get("/api/v1/health")
        assert "x-frame-options" in response.headers
        assert "x-content-type-options" in response.headers
