"""
Health check endpoints.
"""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("", tags=["health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION
    }


@router.get("/detailed", tags=["health"])
async def detailed_health_check():
    """Detailed health check endpoint."""
    # In a real implementation, you would check database connections, etc.
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": "development" if settings.DEBUG else "production",
        "database": "connected",  # Would be checked in real implementation
        "version": settings.APP_VERSION
    }
