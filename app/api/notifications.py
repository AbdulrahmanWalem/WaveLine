"""
Notifications API routes - send, fetch, mark as read endpoints
"""

from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.app import App
from app.models.notification import Notification, StatusEnum
from app.schemas.notification import (
    NotificationCreate,
    NotificationResponse,
    NotificationIdResponse,
    FeedResponse,
    MarkReadResponse
)
from app.services.queue import push_to_queue
from app.api.apps import get_current_app


router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/send", response_model=NotificationIdResponse, status_code=status.HTTP_201_CREATED)
async def send_notification(
    notification_data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_app: App = Depends(get_current_app)
):
    """
    Send a new notification.
    
    The notification will be queued for async delivery by the worker.
    """
    # Create notification with pending status
    new_notification = Notification(
        app_id=current_app.id,
        recipient=notification_data.recipient,
        channel=notification_data.channel,
        title=notification_data.title,
        body=notification_data.body,
        status=StatusEnum.pending
    )
    
    db.add(new_notification)
    await db.commit()
    await db.refresh(new_notification)
    
    # Push to queue for async processing
    push_to_queue(str(new_notification.id))
    
    # Update status to queued
    new_notification.status = StatusEnum.queued
    await db.commit()
    
    return NotificationIdResponse(
        notification_id=new_notification.id,
        status=new_notification.status
    )


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_app: App = Depends(get_current_app)
):
    """
    Get a specific notification by ID.
    
    Returns 404 if not found or belongs to a different app.
    """
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.app_id == current_app.id
            )
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return notification


@router.get("/feed", response_model=FeedResponse)
async def get_notification_feed(
    recipient: str = Query(..., description="Filter by recipient"),
    db: AsyncSession = Depends(get_db),
    current_app: App = Depends(get_current_app)
):
    """
    Get unread in-app notifications for a recipient.
    
    Returns only notifications where:
    - channel = 'inapp'
    - read = false
    - recipient matches
    - belongs to the authenticated app
    """
    result = await db.execute(
        select(Notification)
        .where(
            and_(
                Notification.app_id == current_app.id,
                Notification.recipient == recipient,
                Notification.channel == "inapp",
                Notification.read == False
            )
        )
        .order_by(Notification.created_at.desc())
    )
    
    notifications = result.scalars().all()
    
    return FeedResponse(notifications=notifications)


@router.patch("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_app: App = Depends(get_current_app)
):
    """
    Mark a notification as read.
    
    Returns 404 if not found or belongs to a different app.
    """
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.app_id == current_app.id
            )
        )
    )
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    notification.read = True
    await db.commit()
    
    return MarkReadResponse(status="ok")

