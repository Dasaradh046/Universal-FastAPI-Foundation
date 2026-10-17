"""
Storage integration package.
"""

from app.integrations.storage.factory import get_storage_provider
from app.integrations.storage.service import StorageService

__all__ = ["get_storage_provider", "StorageService"]
