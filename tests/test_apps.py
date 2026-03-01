"""
Tests for apps API endpoints
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create async test client"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_register_app_success(client):
    """Test registering a new app returns an API key"""
    response = await client.post(
        "/apps/register",
        json={"name": "test-app"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "api_key" in data
    assert "app_id" in data
    assert len(data["api_key"]) > 0


@pytest.mark.asyncio
async def test_register_app_duplicate_name(client):
    """Test registering apps with duplicate names works (names aren't unique)"""
    # Register first app
    response1 = await client.post(
        "/apps/register",
        json={"name": "duplicate-name-app"}
    )
    assert response1.status_code == 201
    
    # Register second app with same name
    response2 = await client.post(
        "/apps/register",
        json={"name": "duplicate-name-app"}
    )
    assert response2.status_code == 201
    
    # Both should have different API keys
    assert response1.json()["api_key"] != response2.json()["api_key"]


@pytest.mark.asyncio
async def test_stats_unauthenticated(client):
    """Test stats endpoint returns 401 without auth"""
    response = await client.get("/apps/stats")
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_stats_authenticated(client):
    """Test stats endpoint returns counts for authenticated app"""
    # First register an app to get API key
    register_response = await client.post(
        "/apps/register",
        json={"name": "stats-test-app"}
    )
    api_key = register_response.json()["api_key"]
    
    # Get stats with valid API key
    response = await client.get(
        "/apps/stats",
        headers={"X-API-Key": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total_sent" in data
    assert "total_failed" in data
    assert "total_pending" in data


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health endpoint works"""
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
