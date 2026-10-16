"""
Audit logging — records security-relevant events for compliance and forensics.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.enums import AuditAction
from app.core.logging import get_logger
from app.core.interfaces import IDatabaseService, DatabaseService

logger = get_logger(__name__)


class AuditService:
    """Service for recording audit events with database persistence."""

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
        session: AsyncSession | None = None,
    ) -> None:
        """Record an audit event with full persistence.

        Persists to the audit_logs table for compliance and forensics.
        """
        try:
            # Serialize state snapshots to JSON
            before_json = json.dumps(before_state, default=str) if before_state else None
            after_json = json.dumps(after_state, default=str) if after_state else None

            audit_entry = AuditLog(
                tenant_id=tenant_id,
                action=action,
                resource=resource,
                resource_id=resource_id,
                description=description,
                before_state=before_json,
                after_state=after_json,
                ip_address=ip_address,
                user_agent=user_agent,
                actor_user_id=actor_user_id,
            )

            if session is not None:
                session.add(audit_entry)
                await session.flush()
            else:
                # Fallback: use db_service to get a session
                async with self._db_service.get_session() as db_session:
                    db_session.add(audit_entry)
                    await db_session.flush()

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

        except Exception as exc:
            logger.error(f"Failed to record audit event: {exc}")
            # Don't raise exception as audit failure shouldn't break the main operation
            # In production, we might want to send to a dead letter queue or alerting system


# For backward compatibility, keep the original function
async def record_audit(
    *,
    session: AsyncSession,
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

    Persists to the audit_logs table for compliance and forensics.
    """
    try:
        import json

        before_json = json.dumps(before_state, default=str) if before_state else None
        after_json = json.dumps(after_state, default=str) if after_state else None

        audit_entry = AuditLog(
            tenant_id=tenant_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            description=description,
            before_state=before_json,
            after_state=after_json,
            ip_address=ip_address,
            user_agent=user_agent,
            actor_user_id=actor_user_id,
        )

        session.add(audit_entry)
        await session.flush()

        logger.info(
            "AUDIT: action=%s resource=%s resource_id=%s tenant=%s actor=%s description=%s",
            action.value if hasattr(action, "value") else action,
            resource,
            resource_id,
            tenant_id,
            actor_user_id,
            description,
        )

    except Exception as exc:
        logger.error(f"Failed to record audit event: {exc}")
        # Don't raise exception as audit failure shouldn't break the main operation
        # In production, we might want to send to a dead letter queue or alerting system


def get_core_audit_service() -> AuditService:
    """Dependency to get AuditService instance with database service."""
    from app.core.database import engine
    return AuditService(DatabaseService(engine))


__all__ = [
    "AuditService",
    "get_core_audit_service",
    "record_audit",
]