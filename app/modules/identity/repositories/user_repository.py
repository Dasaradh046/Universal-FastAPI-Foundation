"""
User repository — data-access layer for user entities.

Uses centralized models from ``app.models``. All queries are tenant-scoped
to enforce multi-tenancy isolation.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.encryption import encrypt_field, hash_password
from app.models.enums import Role
from app.models.user import User, UserSession
from app.modules.identity.schemas import UserCreate, UserUpdate

_PII_FIELDS: dict[str, str] = {
    "phone": "phone_encrypted",
    "address": "address_encrypted",
    "date_of_birth": "date_of_birth_encrypted",
    "government_id": "government_id_encrypted",
    "emergency_contact": "emergency_contact_encrypted",
}


class UserRepository:
    """Repository for user entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ---- Lookups ----------------------------------------------------------- #

    async def get(self, id: UUID) -> User | None:
        """Get a user by ID (global lookup)."""
        stmt = select(User).where(User.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_in_tenant(self, tenant_id: UUID, id: UUID) -> User | None:
        """Get a user by ID within a tenant."""
        stmt = select(User).where(User.id == id, User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email (global lookup)."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_tenant(self, tenant_id: UUID, email: str) -> User | None:
        """Get a user by email within a tenant (case-insensitive)."""
        stmt = select(User).where(
            User.tenant_id == tenant_id,
            func.lower(User.email) == func.lower(email),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_employee_id(self, tenant_id: UUID, employee_id: UUID) -> User | None:
        """Get a user by employee ID within a tenant."""
        stmt = (
            select(User)
            .where(User.tenant_id == tenant_id, User.employee_id == employee_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi_by_tenant(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 100,
        role: Role | None = None,
        is_active: bool | None = None,
    ) -> list[User]:
        """Get multiple users for a tenant, optionally filtered by role/status."""
        stmt = (
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if role:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search(
        self,
        tenant_id: UUID,
        query: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        """Search users by email, name, or employee_id within a tenant."""
        pattern = f"%{query}%"
        stmt = (
            select(User)
            .where(User.tenant_id == tenant_id)
            .where(
                func.lower(User.email).like(func.lower(pattern))
                | func.lower(func.coalesce(User.first_name, "")).like(func.lower(pattern))
                | func.lower(func.coalesce(User.last_name, "")).like(func.lower(pattern))
                | func.lower(func.coalesce(User.name, "")).like(func.lower(pattern))
            )
            .order_by(User.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ---- Mutations ---------------------------------------------------------- #

    async def create(self, obj_in: UserCreate, tenant_id: UUID) -> User:
        """Create a new user within a tenant."""
        data = obj_in.model_dump(exclude_unset=True, exclude_none=True)

        # Pop password — the service layer hashes it before calling create,
        # but if a raw password is passed, hash it here too.
        raw_password = data.pop("password", None)
        if raw_password:
            data["password_hash"] = hash_password(raw_password)

        # Move plaintext PII fields to their *_encrypted columns
        encrypted: dict[str, str] = {}
        for plain_field, enc_field in _PII_FIELDS.items():
            if plain_field in data and data[plain_field] is not None:
                encrypted[enc_field] = encrypt_field(data.pop(plain_field))
        data.update(encrypted)

        # Ensure defaults
        data.setdefault("is_active", True)
        data.setdefault("is_super_admin", False)
        data.setdefault("is_demo", False)
        data.setdefault("must_change_password", False)
        data.setdefault("mfa_enrollment_required", False)
        data.setdefault("email_verified", False)
        data.setdefault("failed_login_attempts", 0)

        # If password was set, generate initials from name
        if data.get("first_name") or data.get("last_name"):
            initials = ""
            if data.get("first_name"):
                initials += data["first_name"][0].upper()
            if data.get("last_name"):
                initials += data["last_name"][0].upper()
            if initials:
                data["initials"] = initials

        data["tenant_id"] = tenant_id

        db_obj = User(**data)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: User,
        obj_in: UserUpdate,
    ) -> User:
        """Update a user."""
        data = obj_in.model_dump(exclude_unset=True, exclude_none=True)

        # Handle password separately
        if "password" in data:
            password = data.pop("password")
            if password:
                data["password_hash"] = hash_password(password)
                data["password_changed_at"] = datetime.now(UTC)
                data["must_change_password"] = False

        # Move plaintext PII fields to encrypted columns
        encrypted: dict[str, str] = {}
        for plain_field, enc_field in _PII_FIELDS.items():
            if plain_field in data and data[plain_field] is not None:
                encrypted[enc_field] = encrypt_field(data.pop(plain_field))
            elif plain_field in data and data[plain_field] is None:
                # Setting PII to None — clear the encrypted field
                encrypted[enc_field] = None
        data.update(encrypted)

        # Regenerate initials if name changed
        if "first_name" in data or "last_name" in data:
            first = data.get("first_name") if "first_name" in data else db_obj.first_name
            last = data.get("last_name") if "last_name" in data else db_obj.last_name
            initials = ""
            if first:
                initials += first[0].upper()
            if last:
                initials += last[0].upper()
            if initials:
                db_obj.initials = initials

        for field, value in data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def set_active(self, db_obj: User, is_active: bool) -> User:
        """Activate or deactivate a user."""
        db_obj.is_active = is_active
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def set_super_admin(self, db_obj: User, is_super_admin: bool) -> User:
        """Set or unset the super-admin flag."""
        db_obj.is_super_admin = is_super_admin
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def set_role(self, db_obj: User, role: Role) -> User:
        """Set the user's primary role."""
        db_obj.role = role
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def set_mfa_enrollment_required(self, db_obj: User, required: bool) -> User:
        """Set the MFA enrollment requirement flag."""
        db_obj.mfa_enrollment_required = required
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def set_must_change_password(self, db_obj: User, must_change: bool) -> User:
        """Set the must-change-password flag."""
        db_obj.must_change_password = must_change
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def set_email_verified(self, db_obj: User, verified: bool) -> User:
        """Set the email_verified flag and timestamp."""
        db_obj.email_verified = verified
        if verified:
            db_obj.email_verified_at = datetime.now(UTC)
        else:
            db_obj.email_verified_at = None
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def unlock_account(self, db_obj: User) -> User:
        """Clear lockout state for a user."""
        db_obj.locked_out_at = None
        db_obj.lockout_reason = None
        db_obj.failed_login_attempts = 0
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: User) -> bool:
        """Delete a user."""
        await self.db.delete(db_obj)
        await self.db.flush()
        return True

    async def bulk_set_active(
        self, tenant_id: UUID, user_ids: list[UUID], is_active: bool
    ) -> int:
        """Bulk-set the active flag for users in a tenant."""
        stmt = (
            sa_update(User)
            .where(
                User.tenant_id == tenant_id,
                User.id.in_(user_ids),
            )
            .values(is_active=is_active)
        )
        result = await self.db.execute(stmt)
        return int(result.rowcount)

    # ---- Counts ------------------------------------------------------------ #

    async def count_by_tenant(self, tenant_id: UUID) -> int:
        """Count all users in a tenant."""
        stmt = select(func.count()).where(User.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_active_by_tenant(self, tenant_id: UUID) -> int:
        """Count active users in a tenant."""
        stmt = (
            select(func.count())
            .where(User.tenant_id == tenant_id, User.is_active == True)
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_by_tenant_and_role(self, tenant_id: UUID) -> dict[str, int]:
        """Count users per role in a tenant."""
        stmt = (
            select(User.role, func.count())
            .where(User.tenant_id == tenant_id)
            .group_by(User.role)
        )
        result = await self.db.execute(stmt)
        return {str(role): int(count) for role, count in result.all()}

    async def count_locked_by_tenant(self, tenant_id: UUID) -> int:
        """Count locked-out users in a tenant."""
        stmt = (
            select(func.count())
            .where(
                User.tenant_id == tenant_id,
                User.locked_out_at.is_not(None),
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_mfa_enabled_by_tenant(self, tenant_id: UUID) -> int:
        """Count MFA-enabled users in a tenant."""
        stmt = (
            select(func.count())
            .where(
                User.tenant_id == tenant_id,
                User.two_factor_enabled == True,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_must_change_by_tenant(self, tenant_id: UUID) -> int:
        """Count users with must_change_password flag set."""
        stmt = (
            select(func.count())
            .where(
                User.tenant_id == tenant_id,
                User.must_change_password == True,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def count_mfa_required_by_tenant(self, tenant_id: UUID) -> int:
        """Count users with mfa_enrollment_required flag set."""
        stmt = (
            select(func.count())
            .where(
                User.tenant_id == tenant_id,
                User.mfa_enrollment_required == True,
            )
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    # ---- Sessions ---------------------------------------------------------- #

    async def get_sessions(self, user_id: UUID) -> list[UserSession]:
        """Get all non-revoked sessions for a user."""
        stmt = (
            select(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .order_by(UserSession.last_active_at.desc().nullslast())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class UserRepositoryProtocol(Protocol):
    """Protocol for user repository — enables dependency inversion."""

    async def get(self, id: UUID) -> User | None: ...
    async def get_in_tenant(self, tenant_id: UUID, id: UUID) -> User | None: ...
    async def get_by_email(self, email: str) -> User | None: ...
    async def get_by_email_tenant(self, tenant_id: UUID, email: str) -> User | None: ...
    async def get_by_employee_id(self, tenant_id: UUID, employee_id: UUID) -> User | None: ...
    async def get_multi_by_tenant(self, tenant_id: UUID, skip: int, limit: int, role: Role | None, is_active: bool | None) -> list[User]: ...
    async def search(self, tenant_id: UUID, query: str, skip: int, limit: int) -> list[User]: ...
    async def create(self, obj_in: UserCreate, tenant_id: UUID) -> User: ...
    async def update(self, db_obj: User, obj_in: UserUpdate) -> User: ...
    async def set_active(self, db_obj: User, is_active: bool) -> User: ...
    async def set_super_admin(self, db_obj: User, is_super_admin: bool) -> User: ...
    async def set_role(self, db_obj: User, role: Role) -> User: ...
    async def set_mfa_enrollment_required(self, db_obj: User, required: bool) -> User: ...
    async def set_must_change_password(self, db_obj: User, must_change: bool) -> User: ...
    async def set_email_verified(self, db_obj: User, verified: bool) -> User: ...
    async def unlock_account(self, db_obj: User) -> User: ...
    async def delete(self, db_obj: User) -> bool: ...
    async def bulk_set_active(self, tenant_id: UUID, user_ids: list[UUID], is_active: bool) -> int: ...
    async def count_by_tenant(self, tenant_id: UUID) -> int: ...
    async def count_active_by_tenant(self, tenant_id: UUID) -> int: ...
    async def count_by_tenant_and_role(self, tenant_id: UUID) -> dict[str, int]: ...
    async def count_locked_by_tenant(self, tenant_id: UUID) -> int: ...
    async def count_mfa_enabled_by_tenant(self, tenant_id: UUID) -> int: ...
    async def count_must_change_by_tenant(self, tenant_id: UUID) -> int: ...
    async def count_mfa_required_by_tenant(self, tenant_id: UUID) -> int: ...
    async def get_sessions(self, user_id: UUID) -> list[UserSession]: ...


__all__ = ["UserRepository", "UserRepositoryProtocol"]
