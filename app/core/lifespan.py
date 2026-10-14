"""
Application lifespan events.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from app.core.database import create_db_and_tables, dispose_engine, check_db_connection
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.security import _load_pem

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application lifespan events."""
    # Setup logging
    setup_logging()
    logger.info("Starting up application...")
    
    # Log configuration (excluding secrets)
    logger.info(f"Application: {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # Enforce production secrets in non-local environments
    if not settings.is_local:
        settings.enforce_production_secrets()
        logger.info("Production secrets validated")
    
    # Validate JWT keys if using RS256
    if settings.JWT_ALGORITHM == "RS256":
        try:
            _load_pem(settings.JWT_PRIVATE_KEY_PATH, is_private=True)
            _load_pem(settings.JWT_PUBLIC_KEY_PATH, is_private=False)
            logger.info("RSA keys loaded successfully for RS256 algorithm")
        except Exception as e:
            logger.error(f"Failed to load RSA keys: {e}")
            raise RuntimeError("Failed to load RSA keys for RS256 algorithm") from e
    
    # Create database tables
    try:
        await create_db_and_tables()
        logger.info("Database tables created successfully")
        
        # Verify database connection
        if await check_db_connection():
            logger.info("Database connection verified")
        else:
            logger.warning("Database connection check failed")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    # Additional startup tasks can be added here
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    
    # Dispose of database engine
    try:
        await dispose_engine()
        logger.info("Database connections disposed")
    except Exception as e:
        logger.error(f"Error disposing database engine: {e}")
    
    logger.info("Application shutdown complete")