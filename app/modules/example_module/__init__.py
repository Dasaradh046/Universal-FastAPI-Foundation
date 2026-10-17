"""
Example module package — demonstrates the foundation module patterns.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest

from .api import example_router
from .models import Example
from .permissions import EXAMPLE_READ, EXAMPLE_WRITE
from .repositories import ExampleRepository
from .schemas import (
    ExampleCreate,
    ExampleResponse,
    ExampleUpdate,
)
from .services import ExampleService

# Module manifest - required for registration
MANIFEST = ModuleManifest(
    id="example_module",
    version="1.0.0",
    name="Example Module",
    description="Example module demonstrating the foundation patterns",
    dependencies=[],
    required_capabilities=[],
    optional_capabilities=["audit"],
    router=example_router,
    models=[Example],
    permissions=[EXAMPLE_READ, EXAMPLE_WRITE],
)

# Export public interface
__all__ = [
    "example_router",
    "Example",
    "ExampleCreate",
    "ExampleUpdate",
    "ExampleResponse",
    "ExampleService",
    "ExampleRepository",
    "EXAMPLE_READ",
    "EXAMPLE_WRITE",
    "MANIFEST",
]
