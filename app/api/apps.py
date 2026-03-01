"""
Apps API routes - registration and stats endpoints
"""

import hashlib
import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.app import App
from app.models.notification import Notification, StatusEnum
from app.schemas.app import AppCreate, AppResponse, StatsResponse


router = APIRouter(prefix="/apps", tags=["apps"])


def generate_api_key() -> str:
    """Generate a random API key"""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256"""
    return hashlib.sha256(api_key.encode()).hexdigest()


@router.post("/register", response_model=AppResponse, status_code=status.HTTP_201_CREATED)
async def register_app(
    app_data: AppCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new application and receive an API key.
    
    The API key is returned only once - store it securely!
    """
    # Generate API key
    api_key = generate_api_key()
    api_key_hash = hash_api_key(api_key)
    
    # Create new app
    new_app = App(
        name=app_data.name,
        api_key=api_key_hash
    )
    
    db.add(new_app)
    await db.commit()
    await db.refresh(new_app)
    
    return AppResponse(
        app_id=new_app.id,
        api_key=api_key
    )


async def get_current_app(
    api_key: str,
    db: AsyncSession = Depends(get_db)
) -> App:
    """
    Dependency to get the current authenticated app from API key.
    
    Returns 401 if API key is invalid.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )
    
    api_key_hash = hash_api_key(api_key)
    
    result = await db.execute(
        select(App).where(App.api_key == api_key_hash)
    )
    app = result.scalar_one_or_none()
    
    if not app:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return app


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_app: App = Depends(get_current_app)
):
    """
    Get notification statistics for the authenticated app.
    """
    # Get counts for this app
    result = await db.execute(
        select(
            func.count(Notification.id).filter(Notification.status == StatusEnum.sent),
            func.count(Notification.id).filter(Notification.status == StatusEnum.failed),
            func.count(Notification.id).filter(Notification.status == StatusEnum.pending),
        ).where(Notification.app_id == current_app.id)
    )
    
    row = result.one()
    
    return StatsResponse(
        total_sent=row[0] or 0,
        total_failed=row[1] or 0,
        total_pending=row[2] or 0
    )

