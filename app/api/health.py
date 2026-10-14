"""
Health check endpoints.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from app.core.config import settings
from app.core.database import check_db_connection
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


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
    try:
        # Check database connection
        db_healthy = await check_db_connection()
        
        # Determine overall status
        overall_status = "healthy" if db_healthy else "unhealthy"
        
        # Prepare response
        response: dict[str, Any] = {
            "status": overall_status,
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "database": "connected" if db_healthy else "disconnected",
            "version": settings.APP_VERSION
        }
        
        # Add additional checks as needed
        # For example, Redis, external services, etc.
        
        if overall_status == "unhealthy":
            logger.warning("Health check failed: database disconnected")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unhealthy"
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error during health check: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )


@router.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check endpoint for Kubernetes."""
    try:
        db_ready = await check_db_connection()
        
        if db_ready:
            return {"status": "ready"}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
    except Exception as exc:
        logger.error(f"Error during readiness check: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get("/live", tags=["health"])
async def liveness_check():
    """Liveness check endpoint for Kubernetes."""
    # Simple liveness check - if the app is running, it's alive
    return {"status": "alive"}


__all__ = ["router"]