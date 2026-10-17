"""
Role & Permission schemas for the identity module.

The RoleModel and Permission ORM entities live in ``app.models.user``.
These schemas define the API contract for tenant-scoped role and permission
management.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ResponseEnvelope


class RoleBase(BaseModel):
    """Base role model."""

    code: str = Field(..., min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_\-]*$")
    name: str = Field(..., min_length=1, max_length=160)
    description: str | None = Field(None, max_length=500)

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class RoleCreate(RoleBase):
    """Model for creating a new tenant-scoped role."""


class RoleUpdate(BaseModel):
    """Model for updating a role — all fields optional."""

    code: str | None = Field(None, min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_\-]*$")
    name: str | None = Field(None, min_length=1, max_length=160)
    description: str | None = Field(None, max_length=500)

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)


class RoleInDBBase(BaseModel):
    """Base model for role data stored in DB (read path)."""

    id: UUID
    tenant_id: UUID
    code: str
    name: str
    description: str | None = None
    is_system: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RoleResponse(RoleInDBBase):
    """Model for role returned to client."""
    permissions: list[RolePermissionOut] = Field(default_factory=list)


class RoleInDB(RoleInDBBase):
    """Full role model including internal fields."""


class PermissionOut(BaseModel):
    """A permission within a role listing."""

    id: UUID
    code: str
    name: str
    description: str | None = None
    module: str | None = None
    action: str | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class RolePermissionAssign(BaseModel):
    """Assign a permission to a role."""

    permission_code: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Permission code to grant, e.g. 'users.read', 'tenant:write'",
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class RolePermissionOut(BaseModel):
    """A role-permission link."""

    id: UUID
    role_id: UUID
    permission_id: UUID
    permission: PermissionOut

    model_config = ConfigDict(from_attributes=True)


class RolePermissionListResponse(BaseModel):
    """List of permissions assigned to a role."""

    role_id: UUID
    role_code: str
    permissions: list[PermissionOut]

    model_config = ConfigDict(from_attributes=True)


# ---- Response envelope specializations ---- #

class RoleResponseEnvelope(ResponseEnvelope[RoleResponse]):
    """Single role response envelope."""


class RoleListResponseEnvelope(ResponseEnvelope[list[RoleResponse]]):
    """List of roles response envelope."""


__all__ = [
    "PermissionOut",
    "RoleBase",
    "RoleCreate",
    "RoleInDB",
    "RoleInDBBase",
    "RoleListResponseEnvelope",
    "RolePermissionAssign",
    "RolePermissionListResponse",
    "RolePermissionOut",
    "RoleResponse",
    "RoleResponseEnvelope",
    "RoleUpdate",
]
