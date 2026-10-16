"""
Repository for the example module.

Data-access layer following the Repository pattern with dependency inversion.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.example import Example
from app.modules.example_module.schemas import ExampleCreate, ExampleUpdate


class ExampleRepository:
    """Repository for example entities.

    Implements the data-access layer for the Example entity.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: UUID) -> Optional[Example]:
        """Get an example by ID."""
        stmt = select(Example).where(Example.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str, tenant_id: UUID) -> Optional[Example]:
        """Get an example by name within a tenant."""
        stmt = select(Example).where(
            Example.name == name,
            Example.tenant_id == tenant_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[Example]:
        """Get multiple examples for a tenant."""
        stmt = (
            select(Example)
            .where(Example.tenant_id == tenant_id)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: ExampleCreate, tenant_id: UUID) -> Example:
        """Create a new example."""
        db_obj = Example(
            name=obj_in.name,
            description=obj_in.description,
            tenant_id=tenant_id
        )
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: Example,
        obj_in: ExampleUpdate
    ) -> Example:
        """Update an example."""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: Example) -> bool:
        """Delete an example."""
        await self.db.delete(db_obj)
        await self.db.flush()
        return True


__all__ = ["ExampleRepository"]