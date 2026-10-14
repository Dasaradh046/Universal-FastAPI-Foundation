"""Example module package."""
from __future__ import annotations

from app.modules.module_sdk import ModuleManifest, ModuleRouter

from .router import router
from .schemas import ExampleCreate, ExampleUpdate, ExampleResponse
from .models import Example
from .service import ExampleService
from .repository import ExampleRepository
from .permissions import EXAMPLE_READ, EXAMPLE_WRITE

# Module manifest - required for registration
MANIFEST = ModuleManifest(
    id="example_module",
    version="1.0.0",
    name="Example Module",
    description="Example module demonstrating the foundation patterns",
    dependencies=[],  # Other module IDs this module depends on
    required_capabilities=[],  # Platform capabilities required
    optional_capabilities=["audit"],  # Optional capabilities
    router=router,
    models=[Example],
    permissions=[EXAMPLE_READ, EXAMPLE_WRITE],
    migrations_path="app.modules.example_module.migrations",
)

# Export public interface
__all__ = [
    "router",
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