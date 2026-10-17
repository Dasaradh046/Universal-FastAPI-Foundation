"""
Module SDK for Universal FastAPI Foundation.
Provides base classes and utilities for module development.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict


@dataclass
class ModuleManifest:
    """Manifest for a module, containing metadata and configuration."""

    id: str
    version: str
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)
    optional_capabilities: List[str] = field(default_factory=list)
    router: APIRouter = field(default_factory=APIRouter)
    models: List[type] = field(default_factory=list)
    permissions: List[type] = field(default_factory=list)
    migrations_path: Optional[str] = None

    def __post_init__(self):
        """Validate manifest after initialization."""
        if not self.id:
            raise ValueError("Module ID is required")
        if not self.version:
            raise ValueError("Module version is required")
        if not self.name:
            raise ValueError("Module name is required")
        if not self.router:
            raise ValueError("Module router is required")


@dataclass
class ModuleRouter:
    """Wrapper for module router with additional metadata."""

    router: APIRouter
    prefix: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List = field(default_factory=list)


# Base classes for module components
class ModuleBase:
    """Base class for module components."""

    def __init__(self, module_id: str):
        self.module_id = module_id


class ModuleService(ModuleBase):
    """Base class for module services."""

    def __init__(self, module_id: str):
        super().__init__(module_id)


class ModuleRepository(ModuleBase):
    """Base class for module repositories."""

    def __init__(self, module_id: str):
        super().__init__(module_id)


# Pydantic models for module communication
class ModuleInfo(BaseModel):
    """Information about a module."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    version: str
    name: str
    description: str
    dependencies: List[str]


class ModuleStatus(BaseModel):
    """Status of a module."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str  # active, inactive, maintenance, error
    version: str
    enabled: bool


__all__ = [
    "ModuleManifest",
    "ModuleRouter",
    "ModuleBase",
    "ModuleService",
    "ModuleRepository",
    "ModuleInfo",
    "ModuleStatus",
]
