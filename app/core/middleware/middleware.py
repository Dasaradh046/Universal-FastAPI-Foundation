"""
Custom middleware for the application.
"""
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging
import uuid
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Log request
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as exc:
            # Log exception
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {request.method} {request.url}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "process_time": process_time,
                    "exception": str(exc),
                    "exception_type": type(exc).__name__
                },
                exc_info=True
            )
            raise exc
        
        # Log response
        process_time = time.time() - start_time
        logger.info(
            f"Request completed: {request.method} {request.url}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "status_code": response.status_code,
                "process_time": process_time
            }
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """Middleware for adding process time header."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Remove server header to avoid exposing technology stack
        if "server" in response.headers:
            del response.headers["server"]
        
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware for setting tenant context (placeholder for multi-tenancy)."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # In a real implementation, this would:
        # 1. Extract tenant ID from request (subdomain, header, JWT token)
        # 2. Set the tenant context in the database session
        # 3. Ensure proper cleanup after request
        
        # For now, it's a placeholder that just passes through
        response = await call_next(request)
        return response
