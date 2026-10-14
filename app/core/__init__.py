"""
Core package initialization.
"""
from __future__ import annotations

from app.core.interfaces import (
    IDatabaseService,
    IConfigurationService,
    ISecurityService,
    IAuthService,
    DatabaseService,
    ConfigurationService,
)

# Re-export existing modules for backward compatibility
from app.core import (
    audit,
    cache,
    config,
    database,
    dependencies,
    encryption,
    exceptions,
    lifespan,
    logging,
    middleware,
    permissions,
    role_aliases,
    security,
)

__all__ = [
    # Interfaces
    "IDatabaseService",
    "IConfigurationService",
    "ISecurityService", 
    "IAuthService",
    "DatabaseService",
    "ConfigurationService",
    
    # Existing modules
    "audit",
    "cache",
    "config",
    "database",
    "dependencies",
    "encryption",
    "exceptions",
    "lifespan",
    "logging",
    "middleware",
    "permissions",
    "role_aliases",
    "security",
]