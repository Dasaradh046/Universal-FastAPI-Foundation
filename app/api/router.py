"""
API router registration.
"""
from fastapi import APIRouter

from app.api.health import router as health_router
from app.integrations.email.api.router import router as email_router
from app.modules.audit.api import audit_router_v1 as audit_router
from app.modules.auth.api import auth_router_v1 as auth_router
from app.modules.example_module.api import example_router
from app.modules.identity.api import router as identity_router
from app.modules.notifications.api import (
    notifications_router_v1 as notifications_router,
)
from app.modules.tenant.api import tenant_router_v1 as tenant_router

api_router = APIRouter()

# Include health router
api_router.include_router(health_router, prefix="/health", tags=["health"])

# Include auth router
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Include identity router
api_router.include_router(identity_router, prefix="/identity", tags=["identity"])

# Include notifications router
api_router.include_router(
    notifications_router, prefix="/notifications", tags=["notifications"]
)

# Include audit router
api_router.include_router(audit_router, prefix="/audit", tags=["audit"])

# Include tenant router
api_router.include_router(tenant_router, prefix="/tenant", tags=["tenant"])

# Include example module router
api_router.include_router(example_router, prefix="/examples", tags=["examples"])

# Include email router
api_router.include_router(email_router, prefix="/integrations/email", tags=["email"])

# Additional routers will be included here as modules are added
