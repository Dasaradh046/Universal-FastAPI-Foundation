"""
Audit logging — records security-relevant events for compliance and forensics.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.enums import AuditAction
from app.core.logging import get_logger

logger = get_logger(__name__)


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
    """Record an audit event.

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


__all__ = ["record_audit"]
