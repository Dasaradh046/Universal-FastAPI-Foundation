"""
Service layer for the example module.
"""
from typing import List, Optional
from app.modules.example_module.repository import ExampleRepository
from app.modules.example_module.schemas import ExampleCreate, ExampleUpdate


class ExampleService:
    """Service for example entities."""
    
    def __init__(self, repository: ExampleRepository):
        self.repository = repository
    
    async def get(self, id: int) -> Optional[dict]:
        """Get an example by ID."""
        example = await self.repository.get(id)
        if example:
            return {
                "id": example.id,
                "name": example.name,
                "description": example.description,
                "created_at": example.created_at,
                "updated_at": example.updated_at
            }
        return None
    
    async def get_by_name(self, name: str) -> Optional[dict]:
        """Get an example by name."""
        example = await self.repository.get_by_name(name)
        if example:
            return {
                "id": example.id,
                "name": example.name,
                "description": example.description,
                "created_at": example.created_at,
                "updated_at": example.updated_at
            }
        return None
    
    async def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[dict]:
        """Get multiple examples."""
        examples = await self.repository.get_multi(skip=skip, limit=limit)
        return [
            {
                "id": example.id,
                "name": example.name,
                "description": example.description,
                "created_at": example.created_at,
                "updated_at": example.updated_at
            }
            for example in examples
        ]
    
    async def create(self, obj_in: ExampleCreate) -> dict:
        """Create a new example."""
        example = await self.repository.create(obj_in)
        return {
            "id": example.id,
            "name": example.name,
            "description": example.description,
            "created_at": example.created_at,
            "updated_at": example.updated_at
        }
    
    async def update(
        self, 
        id: int, 
        obj_in: ExampleUpdate
    ) -> Optional[dict]:
        """Update an example."""
        example = await self.repository.get(id)
        if not example:
            return None
        updated_example = await self.repository.update(example, obj_in)
        return {
            "id": updated_example.id,
            "name": updated_example.name,
            "description": updated_example.description,
            "created_at": updated_example.created_at,
            "updated_at": updated_example.updated_at
        }
    
    async def delete(self, id: int) -> bool:
        """Delete an example."""
        example = await self.repository.delete(id)
        return example is not None
