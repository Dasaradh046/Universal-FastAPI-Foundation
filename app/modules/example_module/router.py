"""
API router for the example module.
"""
from __future__ import annotations

from typing import List, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from app.modules.example_module.schemas import ExampleCreate, ExampleUpdate, ExampleResponse
from app.modules.example_module.service import ExampleService
from app.modules.example_module.dependencies import get_example_service_simple
from app.core.dependencies import get_current_user, get_current_active_user
from app.core.security import CurrentUser

router = APIRouter(
    prefix="/examples",
    tags=["examples"],
    dependencies=[Depends(get_current_active_user)],  # Require authentication for all endpoints
)

# Security scheme for documentation
security_scheme = HTTPBearer()


@router.post("", response_model=ExampleResponse, status_code=status.HTTP_201_CREATED)
async def create_example(
    example_in: ExampleCreate,
    service: Annotated[ExampleService, Depends(get_example_service_simple)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Create a new example."""
    example = await service.create(
        example_in=example_in,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )
    return example


@router.get("", response_model=List[ExampleResponse])
async def read_examples(
    service: Annotated[ExampleService, Depends(get_example_service_simple)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
):
    """Retrieve examples for the current tenant."""
    examples = await service.get_multi(
        tenant_id=current_user.tenant_id,
        skip=skip,
        limit=limit,
    )
    return examples


@router.get("/{example_id}", response_model=ExampleResponse)
async def read_example(
    example_id: UUID,
    service: Annotated[ExampleService, Depends(get_example_service_simple)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Retrieve a specific example."""
    example = await service.get(
        id=example_id,
        tenant_id=current_user.tenant_id,  # This will be checked in the service
    )
    # The service will handle tenant validation and raise NotFoundError if needed
    return example


@router.put("/{example_id}", response_model=ExampleResponse)
async def update_example(
    example_id: UUID,
    example_in: ExampleUpdate,
    service: Annotated[ExampleService, Depends(get_example_service_simple)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Update an example."""
    example = await service.update(
        id=example_id,
        obj_in=example_in,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )
    # The service will handle validation and raise appropriate errors
    return example


@router.delete("/{example_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_example(
    example_id: UUID,
    service: Annotated[ExampleService, Depends(get_example_service_simple)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Delete an example."""
    success = await service.delete(
        id=example_id,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )
    # The service will handle validation and raise appropriate errors
    # If we get here, the deletion was successful
    return None


__all__ = ["router"]