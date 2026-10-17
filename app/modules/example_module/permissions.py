"""
Permissions for the example module.
"""

from __future__ import annotations

from app.core.permissions import Permission

EXAMPLE_READ = Permission(
    code="example:read",
    name="Read Examples",
    description="View example entities",
    module="example_module",
    action=None,
)

EXAMPLE_WRITE = Permission(
    code="example:write",
    name="Write Examples",
    description="Create, update, delete example entities",
    module="example_module",
    action=None,
)

EXAMPLE_DELETE = Permission(
    code="example:delete",
    name="Delete Examples",
    description="Delete example entities",
    module="example_module",
    action=None,
)


__all__ = [
    "EXAMPLE_READ",
    "EXAMPLE_WRITE",
    "EXAMPLE_DELETE",
]
