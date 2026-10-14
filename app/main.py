"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from app.core.lifespan import lifespan
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Log settings for debugging
logger.info(f"Database URL: {settings.database_url}")

app = FastAPI(
    title="Universal FastAPI Foundation",
    description="A reusable, integration-ready FastAPI application platform",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint returning basic API information."""
    return {
        "message": "Universal FastAPI Foundation",
        "version": "0.1.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }
