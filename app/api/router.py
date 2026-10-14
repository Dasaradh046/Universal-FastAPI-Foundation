"""
API router registration.
"""
from fastapi import APIRouter
from app.api.health import router as health_router
from app.modules.example_module.router import router as example_router
from app.integrations.email.api.router import router as email_router
from app.modules.auth.api.v1.routes import router as auth_router

api_router = APIRouter()

# Include health router
api_router.include_router(health_router, prefix="/health", tags=["health"])

# Include example module router
api_router.include_router(example_router, prefix="/examples", tags=["examples"])

# Include email router
api_router.include_router(email_router, prefix="/integrations/email", tags=["email"])

# Include auth router
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Additional routers will be included here as modules are added
# Example:
# api_router.include_router(users_router, prefix="/users", tags=["users"])
