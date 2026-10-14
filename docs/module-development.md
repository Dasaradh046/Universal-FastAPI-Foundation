# Module Development Guide

Modules are the primary way to add business functionality to Universal FastAPI Foundation. Each module follows a consistent structure and registers itself with the platform.

## Module Structure

```
modules/
└── my_module/
    ├── __init__.py           # Module registration & manifest
    ├── router.py             # HTTP endpoints (FastAPI router)
    ├── schemas.py            # Request/Response Pydantic models
    ├── models.py             # SQLAlchemy ORM models
    ├── repository.py         # Data access layer
    ├── service.py            # Business logic layer
    ├── dependencies.py       # Module-specific dependencies
    ├── permissions.py        # Module permissions & RBAC
    ├── events.py             # Domain events (optional)
    └── migrations/           # Module-specific Alembic migrations
```

## Module Manifest (`__init__.py`)

Every module must expose a `ModuleManifest` and register its router:

```python
# modules/my_module/__init__.py
from app.modules.module_sdk import ModuleManifest, ModuleRouter

from .router import router
from .schemas import MyEntityCreate, MyEntityRead, MyEntityUpdate
from .models import MyEntity
from .service import MyEntityService
from .repository import MyEntityRepository
from .permissions import MY_ENTITY_READ, MY_ENTITY_WRITE

__all__ = [
    "router",
    "MyEntity",
    "MyEntityCreate",
    "MyEntityRead",
    "MyEntityUpdate",
    "MyEntityService",
    "MyEntityRepository",
    "MY_ENTITY_READ",
    "MY_ENTITY_WRITE",
]

# Module manifest - required for registration
MANIFEST = ModuleManifest(
    id="my_module",
    version="1.0.0",
    name="My Module",
    description="Business logic for managing my entities",
    dependencies=[],  # Other module IDs this module depends on
    required_capabilities=[],  # Platform capabilities required
    optional_capabilities=[],  # Optional capabilities
    router=router,
    models=[MyEntity],
    permissions=[MY_ENTITY_READ, MY_ENTITY_WRITE],
    migrations_path="app.modules.my_module.migrations",
)
```

## Router (`router.py`)

Follow REST conventions with versioned prefix:

```python
# modules/my_module/router.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.permissions import require_permission

from .schemas import MyEntityCreate, MyEntityRead, MyEntityUpdate
from .service import MyEntityService
from .repository import MyEntityRepository
from .dependencies import get_my_entity_service
from .permissions import MY_ENTITY_READ, MY_ENTITY_WRITE

router = APIRouter(prefix="/my-entities", tags=["My Entities"])


@router.post(
    "",
    response_model=MyEntityRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(MY_ENTITY_WRITE))],
)
async def create_entity(
    data: MyEntityCreate,
    service: MyEntityService = Depends(get_my_entity_service),
    current_user = Depends(get_current_user),
):
    """Create a new entity."""
    return await service.create(data, current_user)


@router.get(
    "/{entity_id}",
    response_model=MyEntityRead,
    dependencies=[Depends(require_permission(MY_ENTITY_READ))],
)
async def get_entity(
    entity_id: str,
    service: MyEntityService = Depends(get_my_entity_service),
):
    """Get entity by ID."""
    return await service.get_by_id(entity_id)


@router.get(
    "",
    response_model=list[MyEntityRead],
    dependencies=[Depends(require_permission(MY_ENTITY_READ))],
)
async def list_entities(
    skip: int = 0,
    limit: int = 100,
    service: MyEntityService = Depends(get_my_entity_service),
):
    """List entities with pagination."""
    return await service.list(skip=skip, limit=limit)


@router.patch(
    "/{entity_id}",
    response_model=MyEntityRead,
    dependencies=[Depends(require_permission(MY_ENTITY_WRITE))],
)
async def update_entity(
    entity_id: str,
    data: MyEntityUpdate,
    service: MyEntityService = Depends(get_my_entity_service),
):
    """Update entity."""
    return await service.update(entity_id, data)


@router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission(MY_ENTITY_WRITE))],
)
async def delete_entity(
    entity_id: str,
    service: MyEntityService = Depends(get_my_entity_service),
):
    """Delete entity."""
    await service.delete(entity_id)
```

## Schemas (`schemas.py`)

Use Pydantic v2 models for validation:

```python
# modules/my_module/schemas.py
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field, EmailStr


class MyEntityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    email: EmailStr
    is_active: bool = True


class MyEntityCreate(MyEntityBase):
    """Request schema for creating an entity."""
    pass


class MyEntityUpdate(BaseModel):
    """Request schema for updating an entity."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class MyEntityRead(MyEntityBase):
    """Response schema for entity."""
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

## Models (`models.py`)

SQLAlchemy 2.x async models with UUID primary keys:

```python
# modules/my_module/models.py
from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, TenantMixin


class MyEntity(Base, TimestampMixin, TenantMixin):
    __tablename__ = "my_entities"

    id: Mapped[PG_UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships (if needed)
    # items: Mapped[list["RelatedEntity"]] = relationship(back_populates="my_entity")

    __table_args__ = (
        Index("ix_my_entities_name", "name"),
        Index("ix_my_entities_email", "email", unique=True),
        Index("ix_my_entities_tenant_id", "tenant_id"),
    )
```

**Base mixins from `app.models.base`:**
- `Base` - Declarative base
- `TimestampMixin` - `created_at`, `updated_at` with server defaults
- `TenantMixin` - `tenant_id` with FK to tenants table

## Repository (`repository.py`)

Encapsulate database queries:

```python
# modules/my_module/repository.py
from uuid import UUID
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from .models import MyEntity


class MyEntityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entity: MyEntity) -> MyEntity:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_by_id(self, entity_id: UUID) -> Optional[MyEntity]:
        stmt = select(MyEntity).where(MyEntity.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[MyEntity]:
        stmt = select(MyEntity).where(MyEntity.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        tenant_id: UUID | None = None,
    ) -> list[MyEntity]:
        stmt = select(MyEntity).offset(skip).limit(limit)
        if tenant_id:
            stmt = stmt.where(MyEntity.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, entity: MyEntity) -> MyEntity:
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: MyEntity) -> None:
        await self.session.delete(entity)
        await self.session.flush()
```

## Service (`service.py`)

Business logic, transactions, orchestration:

```python
# modules/my_module/service.py
from uuid import UUID, uuid4
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ConflictError

from .models import MyEntity
from .repository import MyEntityRepository
from .schemas import MyEntityCreate, MyEntityUpdate


class MyEntityService:
    def __init__(self, repository: MyEntityRepository):
        self.repository = repository

    async def create(self, data: MyEntityCreate, current_user) -> MyEntity:
        # Check uniqueness
        existing = await self.repository.get_by_email(data.email)
        if existing:
            raise ConflictError("Entity with this email already exists")

        entity = MyEntity(
            id=uuid4(),
            tenant_id=current_user.tenant_id,
            name=data.name,
            description=data.description,
            email=data.email,
            is_active=data.is_active,
        )
        return await self.repository.create(entity)

    async def get_by_id(self, entity_id: UUID) -> MyEntity:
        entity = await self.repository.get_by_id(entity_id)
        if not entity:
            raise NotFoundError("Entity not found")
        return entity

    async def list(self, skip: int = 0, limit: int = 100, current_user=None) -> list[MyEntity]:
        tenant_id = current_user.tenant_id if current_user else None
        return await self.repository.list(skip=skip, limit=limit, tenant_id=tenant_id)

    async def update(self, entity_id: UUID, data: MyEntityUpdate) -> MyEntity:
        entity = await self.get_by_id(entity_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entity, field, value)

        return await self.repository.update(entity)

    async def delete(self, entity_id: UUID) -> None:
        entity = await self.get_by_id(entity_id)
        await self.repository.delete(entity)
```

## Dependencies (`dependencies.py`)

FastAPI dependency injection:

```python
# modules/my_module/dependencies.py
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.database import get_db
from .repository import MyEntityRepository
from .service import MyEntityService


def get_my_entity_repository(session: AsyncSession = Depends(get_db)) -> MyEntityRepository:
    return MyEntityRepository(session)


@lru_cache(maxsize=1)
def get_my_entity_service(
    repository: MyEntityRepository = Depends(get_my_entity_repository),
) -> MyEntityService:
    return MyEntityService(repository)
```

## Permissions (`permissions.py`)

Define module-specific permissions:

```python
# modules/my_module/permissions.py
from app.core.permissions import Permission

MY_ENTITY_READ = Permission(
    code="my_entity:read",
    name="Read My Entities",
    description="View my entities",
    module="my_module",
)

MY_ENTITY_WRITE = Permission(
    code="my_entity:write",
    name="Write My Entities",
    description="Create, update, delete my entities",
    module="my_module",
)

MY_ENTITY_ADMIN = Permission(
    code="my_entity:admin",
    name="Admin My Entities",
    description="Full admin access to my entities",
    module="my_module",
)
```

## Events (`events.py`) - Optional

Domain events for cross-module communication:

```python
# modules/my_module/events.py
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime


@dataclass
class MyEntityCreated:
    entity_id: UUID
    tenant_id: UUID
    name: str
    created_at: datetime


@dataclass
class MyEntityUpdated:
    entity_id: UUID
    tenant_id: UUID
    changes: dict
    updated_at: datetime


@dataclass
class MyEntityDeleted:
    entity_id: UUID
    tenant_id: UUID
    deleted_at: datetime
```

## Migrations

Each module can have its own migrations:

```bash
# Create migration for module
alembic revision --autogenerate -m "add my_module tables" --version-path app/modules/my_module/migrations

# Or from module directory
cd app/modules/my_module/migrations
alembic revision --autogenerate -m "initial"
```

Module migration files should be independent and not depend on other module migrations.

## Registering Modules

In `app/main.py` or module registry:

```python
from app.modules.my_module import MANIFEST as my_module_manifest
from app.modules.example_module import MANIFEST as example_module_manifest

MODULES = [
    my_module_manifest,
    example_module_manifest,
]

# Register routers
for module in MODULES:
    app.include_router(module.router, prefix=settings.API_V1_STR)

# Register permissions
for module in MODULES:
    for perm in module.permissions:
        permission_registry.register(perm)
```

## Module Rules

1. **Single Responsibility** - One module = one business domain
2. **Explicit Dependencies** - Declare module dependencies in manifest
3. **No Cross-Imports** - Modules cannot import each other's internal code
4. **Interface-Based** - Cross-module communication via events or declared service interfaces
5. **Own Migrations** - Each module owns its tables and migrations
6. **Testable** - Provide test fixtures and mock implementations

## Example Module Reference

See `app/modules/example_module/` for a complete reference implementation following these patterns.