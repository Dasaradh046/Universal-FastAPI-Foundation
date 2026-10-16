"""
Audit logging — records security-relevant events for compliance and forensics.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.models.enums import AuditAction
from app.core.logging import get_logger
from app.core.interfaces import IDatabaseService
from app.core.exceptions import AppException

logger = get_logger(__name__)


class AuditService:
    """Service for recording audit events."""
    
    def __init__(self, db_service: IDatabaseService):
        self._db_service = db_service
    
    async def record_audit(
        self,
        *,
        tenant_id: UUID,
        action: AuditAction,
        resource: str,
        resource_id: str | None = None,
        description: str | None = None,
        before_state: dict[str, Any] | None = None,
        after_state: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        actor_user_id: UUID | None = None,
    ) -> None:
        """Record an audit event.
        
        In a full implementation, this would persist to an audit_log table.
        For the foundation, we log the event and provide the function signature
        so modules can call it without conditional logic.
        """
        try:
            # In a real implementation, we would save to database here
            # For now, we just log the event
            logger.info(
                "AUDIT: action=%s resource=%s resource_id=%s tenant=%s actor=%s description=%s ip=%s",
                action.value if hasattr(action, "value") else action,
                resource,
                resource_id,
                tenant_id,
                actor_user_id,
                description,
                ip_address or "unknown",
            )
            
            # TODO: Implement actual database persistence
            # async with self._db_service.get_session() as session:
            #     audit_entry = AuditLog(
            #         tenant_id=tenant_id,
            #         action=action,
            #         resource=resource,
            #         resource_id=resource_id,
            #         description=description,
            #         before_state=before_state,
            #         after_state=after_state,
            #         ip_address=ip_address,
            #         user_agent=user_agent,
            #         actor_user_id=actor_user_id,
            #         timestamp=datetime.now(UTC)
            #     )
            #     session.add(audit_entry)
            #     await session.commit()
            
        except Exception as exc:
            logger.error(f"Failed to record audit event: {exc}")
            # Don't raise exception as audit failure shouldn't break the main operation
            # In production, we might want to send to a dead letter queue or alerting system


# For backward compatibility, keep the original function
async def record_audit(
    *,
    session: Any,
    tenant_id: UUID,
    actor_user_id: UUID | None = None,
    action: AuditAction,
    resource: str,
    resource_id: str | None = None,
    description: str | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Record an audit event (backward compatibility function).
    
    In a full implementation, this would persist to an audit_log table. For
    the foundation, we log the event and provide the function signature so
    modules can call it without conditional logic.
    """
    logger.info(
        "AUDIT: action=%s resource=%s resource_id=%s tenant=%s actor=%s description=%s",
        action.value if hasattr(action, "value") else action,
        resource,
        resource_id,
        tenant_id,
        actor_user_id,
        description,
    )


__all__ = [
    "AuditService",
    "record_audit",
]