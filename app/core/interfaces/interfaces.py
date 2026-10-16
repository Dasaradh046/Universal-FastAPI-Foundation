"""
Interfaces for core services to ensure SOLID compliance and dependency inversion.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from app.core.config.settings import Settings
from app.core.database.database import AsyncEngine, AsyncSession
from app.core.security.security import CurrentUser


@runtime_checkable
class IDatabaseService(Protocol):
    """Interface for database service."""
    
    async def get_session(self) -> AsyncSession:
        """Get a database session."""
        ...
    
    async def create_tables(self) -> None:
        """Create database tables."""
        ...
    
    async def dispose_engine(self) -> None:
        """Dispose of the database engine."""
        ...
    
    async def check_connection(self) -> bool:
        """Check database connection health."""
        ...


@runtime_checkable
class IConfigurationService(Protocol):
    """Interface for configuration service."""
    
    @property
    def settings(self) -> Settings:
        """Get application settings."""
        ...
    
    def enforce_production_secrets(self) -> None:
        """Enforce production secrets validation."""
        ...


@runtime_checkable
class ISecurityService(Protocol):
    """Interface for security service."""
    
    def create_access_token(
        self,
        subject: str | int,
        tenant_id: str | int,
        role: str,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create an access token."""
        ...
    
    def create_refresh_token(
        self,
        subject: str | int,
        tenant_id: str | int,
        expires_at: Any | None = None,
    ) -> str:
        """Create a refresh token."""
        ...
    
    def decode_token(self, token: str) -> dict[str, Any] | None:
        """Decode and verify a token."""
        ...
    
    def hash_password(self, plain: str) -> str:
        """Hash a password."""
        ...
    
    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify a password."""
        ...


@runtime_checkable
class IAuthService(Protocol):
    """Interface for authentication service."""
    
    async def authenticate_user(self, credentials: dict[str, Any]) -> CurrentUser:
        """Authenticate a user."""
        ...
    
    async def refresh_token(self, refresh_token: str) -> dict[str, str]:
        """Refresh an access token."""
        ...
    
    async def revoke_token(self, token_jti: str) -> None:
        """Revoke a token."""
        ...
    
    def validate_permissions(
        self,
        user: CurrentUser,
        required_permissions: list[str]
    ) -> bool:
        """Validate user permissions."""
        ...


class DatabaseService:
    """Database service implementation."""
    
    def __init__(self, engine: AsyncEngine):
        self._engine = engine
    
    async def get_session(self) -> AsyncSession:
        """Get a database session."""
        from app.core.database.database import session_factory
        async with session_factory() as session:
            return session
    
    async def create_tables(self) -> None:
        """Create database tables."""
        from app.core.database.database import create_db_and_tables
        await create_db_and_tables()
    
    async def dispose_engine(self) -> None:
        """Dispose of the database engine."""
        from app.core.database.database import dispose_engine
        await dispose_engine()
    
    async def check_connection(self) -> bool:
        """Check database connection health."""
        from app.core.database.database import check_db_connection
        return await check_db_connection()


class ConfigurationService:
    """Configuration service implementation."""
    
    def __init__(self, settings: Settings):
        self._settings = settings
    
    @property
    def settings(self) -> Settings:
        """Get application settings."""
        return self._settings
    
    def enforce_production_secrets(self) -> None:
        """Enforce production secrets validation."""
        self._settings.enforce_production_secrets()


# Export interfaces and implementations
__all__ = [
    "IDatabaseService",
    "IConfigurationService", 
    "ISecurityService",
    "IAuthService",
    "DatabaseService",
    "ConfigurationService",
]