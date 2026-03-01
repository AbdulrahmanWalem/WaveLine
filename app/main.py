"""
Waveline - Async Notification Microservice
Main FastAPI application entry point
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.database import engine, Base
from app.api import apps, notifications

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler - creates tables on startup.
    """
    # Startup: create database tables
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")
    
    yield
    
    # Shutdown: close database connections
    logger.info("Shutting down...")
    await engine.dispose()


app = FastAPI(
    title="Waveline",
    description="A self-hostable async notification delivery service",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(apps.router)
app.include_router(notifications.router)


@app.get("/")
async def root():
    return {"message": "Waveline API is running", "status": "healthy"}


@app.get("/health")
async def health():
    return {"status": "ok"}

