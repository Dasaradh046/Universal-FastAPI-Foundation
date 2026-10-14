"""
Permissions for the example module.
"""
from __future__ import annotations

from app.core.permissions import Permission

# Example module permissions
EXAMPLE_READ = Permission(
    code="example:read",
    name="Read Examples",
    description="View example entities",
    module="example_module",
)

EXAMPLE_WRITE = Permission(
    code="example:write",
    name="Write Examples",
    description="Create, update, delete example entities",
    module="example_module",
)

EXAMPLE_DELETE = Permission(
    code="example:delete",
    name="Delete Examples",
    description="Delete example entities",
    module="example_module",
)


__all__ = [
    "EXAMPLE_READ",
    "EXAMPLE_WRITE",
    "EXAMPLE_DELETE",
]