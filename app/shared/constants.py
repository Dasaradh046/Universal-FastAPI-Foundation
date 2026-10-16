"""
Shared constants for the application.
"""

# Pagination defaults
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100

# Token expiration times (in seconds)
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7 days
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24  # 24 hours
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 24      # 24 hours

# Role-related constants
SUPER_ADMIN_ROLE = "platform_owner"  # The role that has super admin privileges

# Status constants
STATUS_ACTIVE = "active"
STATUS_INACTIVE = "inactive"
STATUS_PENDING = "pending"

# File upload constants
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif"}
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}

__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
    "EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS",
    "PASSWORD_RESET_TOKEN_EXPIRE_HOURS",
    "SUPER_ADMIN_ROLE",
    "STATUS_ACTIVE",
    "STATUS_INACTIVE",
    "STATUS_PENDING",
    "MAX_UPLOAD_SIZE",
    "ALLOWED_IMAGE_TYPES",
    "ALLOWED_DOCUMENT_TYPES",
]