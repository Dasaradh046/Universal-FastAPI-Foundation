"""
Main FastAPI application entry point.
"""
from __future__ import annotations

from fastapi import FastAPI, Depends
from app.core.lifespan import lifespan
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import get_logger
from app.core.dependencies import get_current_user
from app.core.security import CurrentUser

# Import module manifests for registration
from app.modules.example_module import MANIFEST as example_module_manifest

logger = get_logger(__name__)

# Register modules
MODULES = [
    example_module_manifest,
]

app = FastAPI(
    title="Universal FastAPI Foundation",
    description="A reusable, integration-ready FastAPI application platform",
    version="0.1.0",
    lifespan=lifespan
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Register module routers
for module in MODULES:
    app.include_router(
        module.router,
        prefix=settings.API_V1_STR,
        dependencies=[Depends(get_current_user)],  # Require authentication for module endpoints
    )


@app.get("/", tags=["root"])
async def root():
    """Root endpoint returning basic API information."""
    return {
        "message": "Universal FastAPI Foundation",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT
    }


@app.get("/info", tags=["info"])
async def app_info(current_user: Annotated[CurrentUser, Depends(get_current_user)]):
    """Application information endpoint (requires authentication)."""
    return {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "role": current_user.role,
            "tenant_id": str(current_user.tenant_id),
        },
        "modules": [
            {
                "id": module.id,
                "name": module.name,
                "version": module.version,
            }
            for module in MODULES
        ]
    }


# Import Annotated for the endpoint above
from typing import Annotated

__all__ = ["app"]