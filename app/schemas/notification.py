"""
Notification Pydantic schemas for request/response validation
"""

from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr
from app.models.notification import ChannelEnum, StatusEnum


class NotificationCreate(BaseModel):
    recipient: str = Field(..., min_length=1, max_length=255)
    channel: ChannelEnum
    title: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1, max_length=5000)


class NotificationResponse(BaseModel):
    id: UUID
    app_id: UUID
    recipient: str
    channel: ChannelEnum
    title: str
    body: str
    status: StatusEnum
    read: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationIdResponse(BaseModel):
    notification_id: UUID
    status: StatusEnum


class FeedResponse(BaseModel):
    notifications: List[NotificationResponse]


class MarkReadResponse(BaseModel):
    status: str

