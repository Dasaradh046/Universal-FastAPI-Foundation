"""
API router for the example module.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.modules.example_module.schemas import ExampleCreate, ExampleUpdate, Example
from app.modules.example_module.service import ExampleService
from app.modules.example_module.dependencies import get_example_service

router = APIRouter()


@router.post("/", response_model=Example, status_code=status.HTTP_201_CREATED)
async def create_example(
    example_in: ExampleCreate,
    service: ExampleService = Depends(get_example_service)
):
    """Create a new example."""
    example = await service.create(example_in)
    return example


@router.get("/", response_model=List[Example])
async def read_examples(
    skip: int = 0,
    limit: int = 100,
    service: ExampleService = Depends(get_example_service)
):
    """Retrieve examples."""
    examples = await service.get_multi(skip=skip, limit=limit)
    return examples


@router.get("/{example_id}", response_model=Example)
async def read_example(
    example_id: int,
    service: ExampleService = Depends(get_example_service)
):
    """Retrieve a specific example."""
    example = await service.get(example_id)
    if example is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Example not found"
        )
    return example


@router.put("/{example_id}", response_model=Example)
async def update_example(
    example_id: int,
    example_in: ExampleUpdate,
    service: ExampleService = Depends(get_example_service)
):
    """Update an example."""
    example = await service.update(example_id, example_in)
    if example is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Example not found"
        )
    return example


@router.delete("/{example_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_example(
    example_id: int,
    service: ExampleService = Depends(get_example_service)
):
    """Delete an example."""
    success = await service.delete(example_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Example not found"
        )
    return None
