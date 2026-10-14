"""
Identity module — tenant and user management APIs.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/tenants")
async def list_tenants():
    """List all tenants."""
    return {"tenants": []}


@router.get("/users")
async def list_users():
    """List all users."""
    return {"users": []}


__all__ = ["router"]