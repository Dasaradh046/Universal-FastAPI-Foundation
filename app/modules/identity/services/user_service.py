"""
User service — business logic layer for user management.

Handles user CRUD, status management (activate/deactivate/lock/unlock),
role assignment, MFA enforcement, password reset flags, and session
management views — all the identity-plane operations that are *not*
authentication (login/logout/MFA challenge live in the auth module).
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from app.core.audit import AuditService
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.core.interfaces import IDatabaseService
from app.core.security.encryption import hash_password
from app.core.security.security import generate_temporary_password
from app.models.enums import Role
from app.models.user import User
from app.modules.identity.events import (
    RoleAssigned,
    RoleRevoked,
    UserActivated,
    UserCreated,
    UserDeactivated,
    UserDeleted,
    UserLocked,
    UserUnlocked,
    UserUpdated,
)
from app.modules.identity.repositories.tenant_repository import TenantRepositoryProtocol
from app.modules.identity.repositories.user_repository import UserRepositoryProtocol
from app.modules.identity.schemas import (
    UserCreate,
    UserResponse,
    UserRoleResponse,
    UserSessionResponse,
    UserStatsResponse,
    UserStatusUpdate,
    UserUpdate,
)


class UserService:
    """Service for user entities.

    Orchestrates business logic, validation, and audit logging for users.
    """

    def __init__(
        self,
        user_repository: UserRepositoryProtocol,
        tenant_repository: TenantRepositoryProtocol,
        audit_service: AuditService | None = None,
        db_service: IDatabaseService | None = None,
    ):
        self.user_repository = user_repository
        self.tenant_repository = tenant_repository
        self._audit_service = audit_service
        self._db_service = db_service
        self._events: list = []

    def _publish_event(self, event) -> None:
        self._events.append(event)

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
            except Exception as exc:  # noqa: BLE001
                from app.core.logging import get_logger
                logger = get_logger(__name__)
                logger.error("Failed to record audit event: %s", exc)

    def _to_dict(self, user: User) -> dict:
        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "name": user.name,
            "job_title": user.job_title,
            "role": user.role.value if user.role else None,
            "employee_id": str(user.employee_id) if user.employee_id else None,
            "is_active": user.is_active,
            "is_super_admin": user.is_super_admin,
            "is_demo": user.is_demo,
            "must_change_password": user.must_change_password,
            "mfa_enrollment_required": user.mfa_enrollment_required,
            "two_factor_enabled": user.two_factor_enabled,
            "email_verified": user.email_verified,
            "tenant_id": str(user.tenant_id),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
            "locked_out_at": user.locked_out_at.isoformat() if user.locked_out_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    async def _verify_tenant(self, tenant_id: UUID) -> None:
        tenant = await self.tenant_repository.get(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant with ID {tenant_id} not found")

    # ---- Queries ----------------------------------------------------------- #

    async def get(self, id: UUID) -> UserResponse:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")
        await self._record_audit(
            action="user.view",
            resource="user",
            resource_id=str(id),
            description=f"Retrieved user {id}",
            tenant_id=user.tenant_id,
        )
        return UserResponse.model_validate(user)

    async def get_in_tenant(self, tenant_id: UUID, id: UUID) -> UserResponse:
        await self._verify_tenant(tenant_id)
        user = await self.user_repository.get_in_tenant(tenant_id, id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found in tenant {tenant_id}")
        await self._record_audit(
            action="user.view",
            resource="user",
            resource_id=str(id),
            description=f"Retrieved user {id} from tenant {tenant_id}",
            tenant_id=tenant_id,
        )
        return UserResponse.model_validate(user)

    async def get_by_email(self, tenant_id: UUID, email: str) -> UserResponse:
        await self._verify_tenant(tenant_id)
        user = await self.user_repository.get_by_email_tenant(tenant_id, email)
        if not user:
            raise NotFoundError(f"User with email '{email}' not found in tenant {tenant_id}")
        return UserResponse.model_validate(user)

    async def get_multi_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        role: Role | None = None,
        is_active: bool | None = None,
    ) -> list[UserResponse]:
        await self._verify_tenant(tenant_id)
        users = await self.user_repository.get_multi_by_tenant(
            tenant_id, skip=skip, limit=limit, role=role, is_active=is_active
        )
        return [UserResponse.model_validate(u) for u in users]

    async def search(
        self,
        tenant_id: UUID,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[UserResponse]:
        await self._verify_tenant(tenant_id)
        if not query or len(query.strip()) < 2:
            raise BadRequestError("Search query must be at least 2 characters")
        users = await self.user_repository.search(tenant_id, query.strip(), skip, limit)
        return [UserResponse.model_validate(u) for u in users]

    async def get_sessions(self, user_id: UUID) -> list[UserSessionResponse]:
        user = await self.user_repository.get(user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")
        sessions = await self.user_repository.get_sessions(user_id)
        return [UserSessionResponse.model_validate(s) for s in sessions]

    async def get_stats(self, tenant_id: UUID) -> UserStatsResponse:
        await self._verify_tenant(tenant_id)

        results = await asyncio.gather(
            self.user_repository.count_by_tenant(tenant_id),
            self.user_repository.count_active_by_tenant(tenant_id),
            self.user_repository.count_locked_by_tenant(tenant_id),
            self.user_repository.count_mfa_enabled_by_tenant(tenant_id),
            self.user_repository.count_mfa_required_by_tenant(tenant_id),
            self.user_repository.count_must_change_by_tenant(tenant_id),
            self.user_repository.count_by_tenant_and_role(tenant_id),
        )

        total, active, locked, mfa, mfa_req, must_change, by_role = results

        return UserStatsResponse(
            tenant_id=tenant_id,
            total_users=total,
            active_users=active,
            inactive_users=total - active,
            locked_out_users=locked,
            mfa_enabled_users=mfa,
            admin_users=by_role.get("admin", 0),
            must_change_password=must_change,
            mfa_enrollment_required=mfa_req,
            by_role=by_role,
        )

    # ---- Mutations --------------------------------------------------------- #

    async def create(
        self,
        obj_in: UserCreate,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        await self._verify_tenant(tenant_id)

        existing = await self.user_repository.get_by_email_tenant(tenant_id, obj_in.email)
        if existing:
            raise ConflictError(f"User with email '{obj_in.email}' already exists in tenant")

        if obj_in.employee_id:
            existing_emp = await self.user_repository.get_by_employee_id(tenant_id, obj_in.employee_id)
            if existing_emp:
                raise ConflictError(f"User with employee ID '{obj_in.employee_id}' already exists in tenant")

        user = await self.user_repository.create(obj_in, tenant_id)

        await self._record_audit(
            action="user.create",
            resource="user",
            resource_id=str(user.id),
            description=f"Created user '{user.email}'",
            after_state=self._to_dict(user),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(UserCreated(
            user_id=user.id, email=user.email, tenant_id=tenant_id,
            created_at=user.created_at or datetime.now(UTC),
        ))
        return UserResponse.model_validate(user)

    async def invite(
        self,
        obj_in: UserCreate,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        await self._verify_tenant(tenant_id)

        existing = await self.user_repository.get_by_email_tenant(tenant_id, obj_in.email)
        if existing:
            raise ConflictError(f"User with email '{obj_in.email}' already exists in tenant")

        obj_in.password = None
        obj_in.must_change_password = True

        user = await self.user_repository.create(obj_in, tenant_id)

        await self._record_audit(
            action="user.invite",
            resource="user",
            resource_id=str(user.id),
            description=f"Invited user '{user.email}'",
            after_state=self._to_dict(user),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(UserCreated(
            user_id=user.id, email=user.email, tenant_id=tenant_id,
            created_at=user.created_at or datetime.now(UTC),
        ))
        return UserResponse.model_validate(user)

    async def update(
        self,
        id: UUID,
        obj_in: UserUpdate,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")

        if obj_in.email and obj_in.email != user.email:
            existing = await self.user_repository.get_by_email(obj_in.email)
            if existing:
                raise ConflictError(f"User with email '{obj_in.email}' already exists")

        before_state = self._to_dict(user)
        updated_user = await self.user_repository.update(user, obj_in)

        await self._record_audit(
            action="user.update",
            resource="user",
            resource_id=str(id),
            description=f"Updated user {id}",
            before_state=before_state,
            after_state=self._to_dict(updated_user),
            tenant_id=updated_user.tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(UserUpdated(
            user_id=updated_user.id, email=updated_user.email,
            tenant_id=updated_user.tenant_id,
            updated_at=updated_user.updated_at or datetime.now(UTC),
        ))
        return UserResponse.model_validate(updated_user)

    async def update_in_tenant(
        self,
        tenant_id: UUID,
        id: UUID,
        obj_in: UserUpdate,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        await self._verify_tenant(tenant_id)
        user = await self.user_repository.get_in_tenant(tenant_id, id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found in tenant {tenant_id}")

        if obj_in.email and obj_in.email != user.email:
            existing = await self.user_repository.get_by_email_tenant(tenant_id, obj_in.email)
            if existing:
                raise ConflictError(f"User with email '{obj_in.email}' already exists in tenant")

        before_state = self._to_dict(user)
        updated_user = await self.user_repository.update(user, obj_in)

        await self._record_audit(
            action="user.update",
            resource="user",
            resource_id=str(id),
            description=f"Updated user {id}",
            before_state=before_state,
            after_state=self._to_dict(updated_user),
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        return UserResponse.model_validate(updated_user)

    async def set_status(
        self,
        id: UUID,
        obj_in: UserStatusUpdate,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")

        before_state = self._to_dict(user)
        updated_user = await self.user_repository.set_active(user, obj_in.is_active)

        await self._record_audit(
            action="user.status_change",
            resource="user",
            resource_id=str(id),
            description=f"Account {'activated' if obj_in.is_active else 'deactivated'}"
            + (f": {obj_in.reason}" if obj_in.reason else ""),
            before_state=before_state,
            after_state=self._to_dict(updated_user),
            tenant_id=updated_user.tenant_id,
            actor_user_id=actor_user_id,
        )

        if obj_in.is_active:
            self._publish_event(UserActivated(
                user_id=user.id, tenant_id=user.tenant_id,
                activated_at=datetime.now(UTC),
            ))
        else:
            self._publish_event(UserDeactivated(
                user_id=user.id, tenant_id=user.tenant_id,
                deactivated_at=datetime.now(UTC),
            ))

        return UserResponse.model_validate(updated_user)

    async def lock_account(
        self,
        id: UUID,
        reason: str | None = None,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")

        if not user.locked_out_at:
            before_state = self._to_dict(user)
            user.locked_out_at = datetime.now(UTC)
            user.lockout_reason = reason or "Administratively locked"
            from app.core.security.lockout import unlock_account as _unlock_account
            _unlock_account(user.tenant_id, user.id)
            await self.user_repository.db.flush()
            await self.user_repository.db.refresh(user)

            await self._record_audit(
                action="user.lock",
                resource="user",
                resource_id=str(id),
                description=f"Account locked: {reason}" if reason else "Account locked",
                before_state=before_state,
                after_state=self._to_dict(user),
                tenant_id=user.tenant_id,
                actor_user_id=actor_user_id,
            )
        self._publish_event(UserLocked(
            user_id=user.id, tenant_id=user.tenant_id,
            reason=reason, locked_at=datetime.now(UTC),
        ))

        return UserResponse.model_validate(user)

    async def unlock_account(
        self,
        id: UUID,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")

        if not user.locked_out_at:
            return UserResponse.model_validate(user)

        before_state = self._to_dict(user)
        updated_user = await self.user_repository.unlock_account(user)

        await self._record_audit(
            action="user.unlock",
            resource="user",
            resource_id=str(id),
            description="Account unlocked",
            before_state=before_state,
            after_state=self._to_dict(updated_user),
            tenant_id=updated_user.tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(UserUnlocked(
            user_id=user.id, tenant_id=user.tenant_id,
            unlocked_at=datetime.now(UTC),
        ))
        return UserResponse.model_validate(updated_user)

    async def set_role(
        self,
        id: UUID,
        role: Role,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")

        before_state = self._to_dict(user)
        updated_user = await self.user_repository.set_role(user, role)

        await self._record_audit(
            action="user.role_change",
            resource="user",
            resource_id=str(id),
            description=f"Primary role set to '{role.value}'",
            before_state=before_state,
            after_state=self._to_dict(updated_user),
            tenant_id=updated_user.tenant_id,
            actor_user_id=actor_user_id,
        )
        return UserResponse.model_validate(updated_user)

    async def set_mfa_requirement(
        self,
        id: UUID,
        required: bool,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")

        before_state = self._to_dict(user)
        updated_user = await self.user_repository.set_mfa_enrollment_required(user, required)

        await self._record_audit(
            action="user.mfa_requirement_change",
            resource="user",
            resource_id=str(id),
            description=f"MFA enrollment required set to {required}",
            before_state=before_state,
            after_state=self._to_dict(updated_user),
            tenant_id=updated_user.tenant_id,
            actor_user_id=actor_user_id,
        )
        return UserResponse.model_validate(updated_user)

    async def set_password_change_required(
        self,
        id: UUID,
        must_change: bool,
        actor_user_id: UUID | None = None,
    ) -> UserResponse:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")

        before_state = self._to_dict(user)
        updated_user = await self.user_repository.set_must_change_password(user, must_change)

        await self._record_audit(
            action="user.password_change_required",
            resource="user",
            resource_id=str(id),
            description=f"Must change password set to {must_change}",
            before_state=before_state,
            after_state=self._to_dict(updated_user),
            tenant_id=updated_user.tenant_id,
            actor_user_id=actor_user_id,
        )
        return UserResponse.model_validate(updated_user)

    async def reset_password(
        self,
        id: UUID,
        new_password: str | None = None,
        must_change_password: bool = True,
        actor_user_id: UUID | None = None,
    ) -> dict:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")

        temp_password = new_password or generate_temporary_password()
        hashed = hash_password(temp_password)

        before_state = self._to_dict(user)

        from sqlalchemy import update
        stmt = (
            update(User)
            .where(User.id == user.id)
            .values(
                password_hash=hashed,
                password_changed_at=datetime.now(UTC),
                must_change_password=must_change_password,
            )
        )
        await self.user_repository.db.execute(stmt)

        await self._record_audit(
            action="user.password_reset",
            resource="user",
            resource_id=str(id),
            description="Password reset by administrator",
            before_state=before_state,
            after_state={"must_change_password": must_change_password},
            tenant_id=user.tenant_id,
            actor_user_id=actor_user_id,
        )

        return {
            "user_id": str(user.id),
            "email": user.email,
            "temporary_password": temp_password,
            "must_change_password": must_change_password,
        }

    async def bulk_update_status(
        self,
        tenant_id: UUID,
        user_ids: list[UUID],
        is_active: bool | None = None,
        mfa_enrollment_required: bool | None = None,
        actor_user_id: UUID | None = None,
    ) -> dict:
        await self._verify_tenant(tenant_id)

        values: dict = {}
        if is_active is not None:
            values["is_active"] = is_active
        if mfa_enrollment_required is not None:
            values["mfa_enrollment_required"] = mfa_enrollment_required

        if not values:
            return {"updated": 0, "total_requested": len(user_ids)}

        from sqlalchemy import update
        stmt = (
            update(User)
            .where(
                User.tenant_id == tenant_id,
                User.id.in_(user_ids),
            )
            .values(**values)
        )
        result = await self.user_repository.db.execute(stmt)
        updated = int(result.rowcount)

        await self._record_audit(
            action="user.bulk_status_update",
            resource="user",
            description=f"Bulk-updated {updated} users in tenant {tenant_id}",
            after_state={"is_active": is_active, "mfa_enrollment_required": mfa_enrollment_required},
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )

        return {"updated": updated, "total_requested": len(user_ids)}

    # ---- Role assignment (additional roles) -------------------------------- #

    async def assign_role(
        self,
        user_id: UUID,
        role_code: str,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
    ) -> bool:
        user = await self.user_repository.get_in_tenant(tenant_id, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found in tenant {tenant_id}")

        role_repo = self._get_role_repository()
        role = await role_repo.get_by_code(tenant_id, role_code)
        if not role:
            raise NotFoundError(f"Role with code '{role_code}' not found in tenant {tenant_id}")

        await role_repo.assign_user_role(user_id, role.id, tenant_id)

        await self._record_audit(
            action="user.role_assign",
            resource="user",
            resource_id=str(user_id),
            description=f"Assigned role '{role_code}' to user",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(RoleAssigned(
            user_id=user_id, role_id=role.id, role_code=role_code,
            tenant_id=tenant_id, assigned_at=datetime.now(UTC),
        ))
        return True

    async def revoke_role(
        self,
        user_id: UUID,
        role_code: str,
        tenant_id: UUID,
        actor_user_id: UUID | None = None,
    ) -> bool:
        user = await self.user_repository.get_in_tenant(tenant_id, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found in tenant {tenant_id}")

        role_repo = self._get_role_repository()
        role = await role_repo.get_by_code(tenant_id, role_code)
        if not role:
            raise NotFoundError(f"Role with code '{role_code}' not found in tenant {tenant_id}")

        await role_repo.remove_user_role(user_id, role.id)

        await self._record_audit(
            action="user.role_revoke",
            resource="user",
            resource_id=str(user_id),
            description=f"Revoked role '{role_code}' from user",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(RoleRevoked(
            user_id=user_id, role_id=role.id, role_code=role_code,
            tenant_id=tenant_id, revoked_at=datetime.now(UTC),
        ))
        return True

    async def list_user_roles(self, user_id: UUID, tenant_id: UUID) -> list[UserRoleResponse]:
        user = await self.user_repository.get_in_tenant(tenant_id, user_id)
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found in tenant {tenant_id}")

        role_repo = self._get_role_repository()
        rows = await role_repo.get_user_roles(user_id)

        results: list[UserRoleResponse] = []
        for role_model, link in rows:
            results.append(UserRoleResponse(
                id=role_model.id,
                code=role_model.code,
                name=role_model.name,
                is_system=role_model.is_system,
                assigned_at=link.created_at,
            ))
        return results

    def _get_role_repository(self):
        from app.modules.identity.repositories.role_repository import RoleRepository
        return RoleRepository(self.user_repository.db)

    # ---- Delete ------------------------------------------------------------ #

    async def delete(
        self,
        id: UUID,
        actor_user_id: UUID | None = None,
    ) -> bool:
        user = await self.user_repository.get(id)
        if not user:
            raise NotFoundError(f"User with ID {id} not found")

        before_state = self._to_dict(user)
        result = await self.user_repository.delete(user)

        await self._record_audit(
            action="user.delete",
            resource="user",
            resource_id=str(id),
            description=f"Deleted user '{user.email}'",
            before_state=before_state,
            after_state=None,
            tenant_id=user.tenant_id,
            actor_user_id=actor_user_id,
        )
        self._publish_event(UserDeleted(
            user_id=user.id, email=user.email,
            tenant_id=user.tenant_id, deleted_at=datetime.now(UTC),
        ))
        return result


__all__ = ["UserService"]
