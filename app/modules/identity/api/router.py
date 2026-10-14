"""
Identity module API router.
"""
from fastapi import APIRouter
from app.modules.identity.api.v1.routes import router as identity_router_v1

router = APIRouter()
router.include_router(identity_router_v1, prefix="/v1", tags=["identity"])

__all__ = ["router"]