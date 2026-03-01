"""
App Pydantic schemas for request/response validation
"""

from uuid import UUID
from pydantic import BaseModel, Field


class AppCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class AppResponse(BaseModel):
    app_id: UUID
    api_key: str

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_sent: int
    total_failed: int
    total_pending: int

