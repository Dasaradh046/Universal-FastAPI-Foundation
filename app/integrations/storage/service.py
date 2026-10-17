"""
Storage service layer.
"""

from typing import Optional

from app.core.logging import get_logger
from app.integrations.storage.contracts import (
    StorageUploadResult,
)
from app.integrations.storage.factory import get_storage_provider

logger = get_logger(__name__)


class StorageService:
    """Service for file/object storage operations."""

    def __init__(self):
        self.provider = get_storage_provider()

    async def upload_file(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> StorageUploadResult:
        """Upload a file to storage.

        Args:
            bucket: Target bucket name
            key: Object key/path
            data: File data as bytes
            content_type: MIME type of the file

        Returns:
            Upload result
        """
        return await self.provider.upload(bucket, key, data, content_type)

    async def download_file(self, bucket: str, key: str) -> bytes:
        """Download a file from storage.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            File data as bytes

        Raises:
            StorageError: If the file does not exist
        """
        return await self.provider.download(bucket, key)

    async def delete_file(self, bucket: str, key: str) -> bool:
        """Delete a file from storage.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            True if the file was deleted
        """
        return await self.provider.delete(bucket, key)

    async def file_exists(self, bucket: str, key: str) -> bool:
        """Check if a file exists in storage.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            True if the file exists
        """
        return await self.provider.exists(bucket, key)

    async def get_file_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Get a URL for accessing a file.

        Args:
            bucket: Bucket name
            key: Object key/path
            expires_in: URL expiration in seconds (for presigned URLs)

        Returns:
            URL string
        """
        return await self.provider.get_url(bucket, key, expires_in)


__all__ = ["StorageService"]
