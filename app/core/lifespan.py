"""
Application lifespan events.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.database import create_db_and_tables, dispose_engine
from app.core.config import settings
from app.core.logging import setup_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    
    # Create database tables
    try:
        await create_db_and_tables()
        logger.info("Database tables created successfully")
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


__all__ = ["lifespan"]
