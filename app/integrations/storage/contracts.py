"""
Storage service contracts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Protocol

from pydantic import BaseModel


class StorageObject(BaseModel):
    """Represents a stored object."""

    key: str
    bucket: str
    size: int
    content_type: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    url: Optional[str] = None


class StorageUploadResult(BaseModel):
    """Result of uploading an object."""

    key: str
    bucket: str
    size: int
    etag: Optional[str] = None
    url: Optional[str] = None


class StorageProvider(Protocol):
    """Protocol defining the storage provider interface."""

    async def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> StorageUploadResult:
        """Upload an object to storage.

        Args:
            bucket: Target bucket name
            key: Object key/path
            data: Object data as bytes
            content_type: MIME type of the object

        Returns:
            Upload result with key, bucket, size, etag, and optional URL

        Raises:
            StorageError: If the upload fails
        """
        ...

    async def download(self, bucket: str, key: str) -> bytes:
        """Download an object from storage.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            Object data as bytes

        Raises:
            StorageError: If the download fails or object not found
        """
        ...

    async def delete(self, bucket: str, key: str) -> bool:
        """Delete an object from storage.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            True if the object was deleted, False if it didn't exist

        Raises:
            StorageError: If the deletion fails
        """
        ...

    async def exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in storage.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            True if the object exists, False otherwise
        """
        ...

    async def get_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Get a presigned URL for an object.

        Args:
            bucket: Bucket name
            key: Object key/path
            expires_in: URL expiration in seconds

        Returns:
            Presigned URL string

        Raises:
            StorageError: If the URL cannot be generated
        """
        ...


class StorageError(Exception):
    """Exception raised when storage operations fail."""

    def __init__(self, message: str, provider_error_code: Optional[str] = None):
        super().__init__(message)
        self.provider_error_code = provider_error_code


class StorageBaseService(ABC):
    """Abstract base class for storage services."""

    @abstractmethod
    async def upload_file(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> StorageUploadResult:
        pass

    @abstractmethod
    async def download_file(self, bucket: str, key: str) -> bytes:
        pass

    @abstractmethod
    async def delete_file(self, bucket: str, key: str) -> bool:
        pass

    @abstractmethod
    async def file_exists(self, bucket: str, key: str) -> bool:
        pass
