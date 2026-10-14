"""
Repository for the example module.
"""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.example_module.models import Example
from app.modules.example_module.schemas import ExampleCreate, ExampleUpdate


class ExampleRepository:
    """Repository for example entities."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get(self, id: int) -> Optional[Example]:
        """Get an example by ID."""
        result = await self.db.execute(select(Example).where(Example.id == id))
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str) -> Optional[Example]:
        """Get an example by name."""
        result = await self.db.execute(select(Example).where(Example.name == name))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Example]:
        """Get multiple examples."""
        result = await self.db.execute(
            select(Example).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def create(self, obj_in: ExampleCreate) -> Example:
        """Create a new example."""
        db_obj = Example(
            name=obj_in.name,
            description=obj_in.description
        )
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, 
        db_obj: Example, 
        obj_in: ExampleUpdate
    ) -> Example:
        """Update an example."""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def delete(self, id: int) -> Optional[Example]:
        """Delete an example."""
        db_obj = await self.get(id)
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.commit()
        return db_obj
