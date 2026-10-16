"""
API router for the example module.

All endpoints use the application-wide ResponseEnvelope for consistent responses.
"""

from __future__ import annotations

from typing import List, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from app.modules.example_module.schemas import (
    ExampleCreate,
    ExampleUpdate,
    ExampleResponse,
    ExampleResponseEnvelope,
    ExampleListResponseEnvelope,
)
from app.modules.example_module.service import ExampleService
from app.modules.example_module.dependencies import get_example_service
from app.core.dependencies import get_current_user, get_current_active_user
from app.core.security import CurrentUser
from app.schemas.common import ok, paginated

router = APIRouter(
    prefix="/examples",
    tags=["examples"],
    dependencies=[Depends(get_current_active_user)],  # Require authentication for all endpoints
)


@router.post("", response_model=ExampleResponseEnvelope, status_code=status.HTTP_201_CREATED)
async def create_example(
    example_in: ExampleCreate,
    service: Annotated[ExampleService, Depends(get_example_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Create a new example."""
    example = await service.create(
        example_in=example_in,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )
    return created(data=example, message="Example created successfully")


@router.get("", response_model=ExampleListResponseEnvelope)
async def read_examples(
    service: Annotated[ExampleService, Depends(get_example_service)],
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
    # For pagination, we'd need total count - simplified for now
    return ok(data=examples, message="Examples retrieved successfully")


@router.get("/{example_id}", response_model=ExampleResponseEnvelope)
async def read_example(
    example_id: UUID,
    service: Annotated[ExampleService, Depends(get_example_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Retrieve a specific example."""
    example = await service.get(
        id=example_id,
        tenant_id=current_user.tenant_id,
    )
    return ok(data=example, message="Example retrieved successfully")


@router.put("/{example_id}", response_model=ExampleResponseEnvelope)
async def update_example(
    example_id: UUID,
    example_in: ExampleUpdate,
    service: Annotated[ExampleService, Depends(get_example_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Update an example."""
    example = await service.update(
        id=example_id,
        obj_in=example_in,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )
    return ok(data=example, message="Example updated successfully")


@router.delete("/{example_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_example(
    example_id: UUID,
    service: Annotated[ExampleService, Depends(get_example_service)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """Delete an example."""
    await service.delete(
        id=example_id,
        tenant_id=current_user.tenant_id,
        actor_user_id=current_user.id,
    )
    # 204 No Content - no response body
    return None


__all__ = ["router"]