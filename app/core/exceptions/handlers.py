"""
Exception handler registration.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

from app.core.exceptions.exceptions import (
    app_exception_handler,
    http_exception_handler,
    general_exception_handler,
    AppException,
    HTTPException as CustomHTTPException,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI):
    """Register exception handlers with the FastAPI application."""
    # Custom application exceptions
    app.add_exception_handler(AppException, app_exception_handler)
    
    # Starlette HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # FastAPI HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # FastAPI validation errors
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    
    # General exception handler (catch-all)
    app.add_exception_handler(Exception, general_exception_handler)


async def _validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle Pydantic validation errors."""
    if not isinstance(exc, RequestValidationError):
        raise exc
    logger.warning("Validation error: %s", exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
        },
    )
