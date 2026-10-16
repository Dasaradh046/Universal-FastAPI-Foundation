"""
Service layer for the example module.

Follows SOLID principles:
- SRP: Only handles example domain logic
- OCP: Extensible via interface implementation
- LSP: Repository interface can be swapped
- ISP: Depends on abstract repository interface
- DIP: Depends on abstractions (repository, audit), not concretions
"""

from __future__ import annotations

from typing import List, Optional, Protocol
from uuid import UUID

from app.core.audit import AuditService
from app.core.exceptions import NotFoundError, ConflictError
from app.core.interfaces import IDatabaseService
from app.modules.example_module.repository import ExampleRepository
from app.modules.example_module.schemas import ExampleCreate, ExampleUpdate, ExampleResponse


class ExampleRepositoryProtocol(Protocol):
    """Protocol for example repository - enables dependency inversion."""

    async def get(self, id: UUID) -> Optional[Example]: ...
    async def get_by_name(self, name: str, tenant_id: UUID) -> Optional[Example]: ...
    async def get_multi(self, tenant_id: UUID, skip: int, limit: int) -> List[Example]: ...
    async def create(self, obj_in: ExampleCreate, tenant_id: UUID) -> Example: ...
    async def update(self, db_obj: Example, obj_in: ExampleUpdate) -> Example: ...
    async def delete(self, db_obj: Example) -> bool: ...


class ExampleService:
    """Service for example entities.

    Orchestrates business logic, validation, and audit logging.
    """

    def __init__(
        self,
        repository: ExampleRepository,
        audit_service: AuditService | None = None,
        db_service: IDatabaseService | None = None
    ):
        self.repository = repository
        self._audit_service = audit_service
        self._db_service = db_service

    async def _record_audit(
        self,
        action: str,
        resource: str,
        resource_id: str | None = None,
        description: str | None = None,
        before_state: dict | None = None,
        after_state: dict | None = None,
        tenant_id: UUID | None = None,
        actor_user_id: UUID | None = None,
    ) -> None:
        """Record an audit event if audit service is available."""
        if self._audit_service and tenant_id:
            try:
                await self._audit_service.record_audit(
                    tenant_id=tenant_id,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    description=description,
                    before_state=before_state,
                    after_state=after_state,
                    actor_user_id=actor_user_id,
                )
            except Exception as exc:
                # Don't let audit failures break the main operation
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to record audit event: {exc}")

    def _to_dict(self, example: Example) -> dict:
        """Convert example to dictionary for audit logging."""
        return {
            "id": str(example.id),
            "name": example.name,
            "description": example.description,
            "tenant_id": str(example.tenant_id),
            "created_at": example.created_at.isoformat() if example.created_at else None,
            "updated_at": example.updated_at.isoformat() if example.updated_at else None,
        }

    async def get(self, id: UUID, tenant_id: UUID) -> ExampleResponse:
        """Get an example by ID within a tenant."""
        example = await self.repository.get(id)
        if not example or example.tenant_id != tenant_id:
            raise NotFoundError(f"Example with ID {id} not found in tenant {tenant_id}")

        await self._record_audit(
            action="example.view",
            resource="example",
            resource_id=str(id),
            description=f"Retrieved example {id}",
            tenant_id=tenant_id,
        )

        return ExampleResponse.model_validate(example)

    async def get_by_name(self, name: str, tenant_id: UUID) -> ExampleResponse:
        """Get an example by name within a tenant."""
        example = await self.repository.get_by_name(name, tenant_id)
        if not example:
            raise NotFoundError(f"Example with name '{name}' not found in tenant {tenant_id}")

        await self._record_audit(
            action="example.view_by_name",
            resource="example",
            resource_id=str(example.id),
            description=f"Retrieved example by name '{name}'",
            tenant_id=tenant_id,
        )

        return ExampleResponse.model_validate(example)

    async def get_multi(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[ExampleResponse]:
        """Get multiple examples for a tenant."""
        examples = await self.repository.get_multi(tenant_id, skip=skip, limit=limit)
        examples_response = [ExampleResponse.model_validate(example) for example in examples]

        await self._record_audit(
            action="example.list",
            resource="example",
            description=f"Listed {len(examples)} examples",
            tenant_id=tenant_id,
        )

        return examples_response

    async def create(
        self,
        obj_in: ExampleCreate,
        tenant_id: UUID,
        actor_user_id: UUID | None = None
    ) -> ExampleResponse:
        """Create a new example."""
        # Check for duplicate name within tenant
        existing = await self.repository.get_by_name(obj_in.name, tenant_id)
        if existing:
            raise ConflictError(f"Example with name '{obj_in.name}' already exists in tenant {tenant_id}")

        example = await self.repository.create(obj_in, tenant_id)

        await self._record_audit(
            action="example.create",
            resource="example",
            resource_id=str(example.id),
            description=f"Created example '{example.name}'",
            before_state=None,
            after_state=self._to_dict(example),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )

        return ExampleResponse.model_validate(example)

    async def update(
        self,
        id: UUID,
        obj_in: ExampleUpdate,
        tenant_id: UUID,
        actor_user_id: UUID | None = None
    ) -> ExampleResponse:
        """Update an example."""
        # Get the existing example
        example = await self.repository.get(id)
        if not example or example.tenant_id != tenant_id:
            raise NotFoundError(f"Example with ID {id} not found in tenant {tenant_id}")

        # Check for duplicate name if name is being updated
        if obj_in.name and obj_in.name != example.name:
            existing = await self.repository.get_by_name(obj_in.name, tenant_id)
            if existing and existing.id != id:
                raise ConflictError(f"Example with name '{obj_in.name}' already exists in tenant {tenant_id}")

        # Store before state for audit
        before_state = self._to_dict(example)

        # Update the example
        updated_example = await self.repository.update(example, obj_in)

        await self._record_audit(
            action="example.update",
            resource="example",
            resource_id=str(id),
            description=f"Updated example {id}",
            before_state=before_state,
            after_state=self._to_dict(updated_example),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )

        return ExampleResponse.model_validate(updated_example)

    async def delete(
        self,
        id: UUID,
        tenant_id: UUID,
        actor_user_id: UUID | None = None
    ) -> bool:
        """Delete an example."""
        # Get the existing example
        example = await self.repository.get(id)
        if not example or example.tenant_id != tenant_id:
            raise NotFoundError(f"Example with ID {id} not found in tenant {tenant_id}")

        # Store before state for audit
        before_state = self._to_dict(example)

        # Delete the example
        result = await self.repository.delete(example)

        await self._record_audit(
            action="example.delete",
            resource="example",
            resource_id=str(id),
            description=f"Deleted example {id}",
            before_state=before_state,
            after_state=None,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )

        return result is not None


__all__ = ["ExampleService", "ExampleRepositoryProtocol"]