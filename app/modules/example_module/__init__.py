"""
Example module package — demonstrates the foundation module patterns.
"""

from __future__ import annotations

from app.modules.module_sdk import ModuleManifest

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
    dependencies=[],
    required_capabilities=[],
    optional_capabilities=["audit"],
    router=router,
    models=[Example],
    permissions=[EXAMPLE_READ, EXAMPLE_WRITE],
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
