"""
Tests for notifications API endpoints
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


@pytest.fixture
async def test_app(client):
    """Create a test app and return its API key"""
    response = await client.post(
        "/apps/register",
        json={"name": "notification-test-app"}
    )
    return response.json()


@pytest.mark.asyncio
async def test_send_notification_success(client, test_app):
    """Test sending a notification succeeds"""
    response = await client.post(
        "/notifications/send",
        headers={"X-API-Key": test_app["api_key"]},
        json={
            "recipient": "test@example.com",
            "channel": "email",
            "title": "Test Notification",
            "body": "This is a test notification"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "notification_id" in data
    assert data["status"] in ["pending", "queued"]


@pytest.mark.asyncio
async def test_send_notification_unauthenticated(client):
    """Test sending notification without auth returns 401"""
    response = await client.post(
        "/notifications/send",
        json={
            "recipient": "test@example.com",
            "channel": "email",
            "title": "Test Notification",
            "body": "This is a test notification"
        }
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_send_notification_invalid_channel(client, test_app):
    """Test sending notification with invalid channel fails"""
    response = await client.post(
        "/notifications/send",
        headers={"X-API-Key": test_app["api_key"]},
        json={
            "recipient": "test@example.com",
            "channel": "invalid_channel",
            "title": "Test Notification",
            "body": "This is a test notification"
        }
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_notification_success(client, test_app):
    """Test getting a notification by ID"""
    # First create a notification
    send_response = await client.post(
        "/notifications/send",
        headers={"X-API-Key": test_app["api_key"]},
        json={
            "recipient": "test@example.com",
            "channel": "email",
            "title": "Get Test",
            "body": "Testing GET endpoint"
        }
    )
    notification_id = send_response.json()["notification_id"]
    
    # Then get it
    response = await client.get(
        f"/notifications/{notification_id}",
        headers={"X-API-Key": test_app["api_key"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == notification_id


@pytest.mark.asyncio
async def test_get_notification_wrong_app(client, test_app):
    """Test getting notification from wrong app returns 404"""
    # Create another app
    other_app_response = await client.post(
        "/apps/register",
        json={"name": "other-app"}
    )
    other_api_key = other_app_response.json()["api_key"]
    
    # Create notification with first app
    send_response = await client.post(
        "/notifications/send",
        headers={"X-API-Key": test_app["api_key"]},
        json={
            "recipient": "test@example.com",
            "channel": "email",
            "title": "Secret Notification",
            "body": "This should not be visible"
        }
    )
    notification_id = send_response.json()["notification_id"]
    
    # Try to get with other app - should return 404
    response = await client.get(
        f"/notifications/{notification_id}",
        headers={"X-API-Key": other_api_key}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_feed_returns_only_unread(client, test_app):
    """Test feed returns only unread in-app notifications"""
    # Send an in-app notification
    await client.post(
        "/notifications/send",
        headers={"X-API-Key": test_app["api_key"]},
        json={
            "recipient": "feeduser@example.com",
            "channel": "inapp",
            "title": "In-App Test",
            "body": "Testing feed endpoint"
        }
    )
    
    # Get the feed
    response = await client.get(
        f"/notifications/feed?recipient=feeduser@example.com",
        headers={"X-API-Key": test_app["api_key"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "notifications" in data
    assert len(data["notifications"]) > 0


@pytest.mark.asyncio
async def test_mark_as_read(client, test_app):
    """Test marking a notification as read"""
    # Create an in-app notification
    send_response = await client.post(
        "/notifications/send",
        headers={"X-API-Key": test_app["api_key"]},
        json={
            "recipient": "markread@example.com",
            "channel": "inapp",
            "title": "Mark Read Test",
            "body": "Testing mark as read"
        }
    )
    notification_id = send_response.json()["notification_id"]
    
    # Mark as read
    response = await client.patch(
        f"/notifications/{notification_id}/read",
        headers={"X-API-Key": test_app["api_key"]}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
