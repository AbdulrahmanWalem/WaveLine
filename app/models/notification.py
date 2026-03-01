"""
Notification and DeliveryLog models
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class ChannelEnum(str, enum.Enum):
    email = "email"
    inapp = "inapp"
    webhook = "webhook"


class StatusEnum(str, enum.Enum):
    pending = "pending"
    queued = "queued"
    sent = "sent"
    failed = "failed"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id"), nullable=False)
    recipient = Column(String(255), nullable=False)
    channel = Column(SQLEnum(ChannelEnum), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(SQLEnum(StatusEnum), default=StatusEnum.pending, nullable=False)
    read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to delivery logs
    delivery_logs = relationship("DeliveryLog", back_populates="notification", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Notification(id={self.id}, channel={self.channel}, status={self.status})>"


class DeliveryLog(Base):
    __tablename__ = "delivery_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False)
    attempt = Column(Integer, nullable=False, default=1)
    status = Column(SQLEnum(StatusEnum), nullable=False)
    error_message = Column(Text, nullable=True)
    attempted_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to notification
    notification = relationship("Notification", back_populates="delivery_logs")

    def __repr__(self):
        return f"<DeliveryLog(notification_id={self.notification_id}, attempt={self.attempt}, status={self.status})>"

