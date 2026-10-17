"""
Local filesystem storage provider.

Stores objects on the local filesystem. Suitable for development and
single-node deployments.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.storage.contracts import (
    StorageError,
    StorageProvider,
    StorageUploadResult,
)

logger = get_logger(__name__)


class LocalStorageProvider(StorageProvider):
    """Local filesystem storage provider implementation."""

    def __init__(self):
        self.base_path = Path(settings.LOCAL_STORAGE_PATH).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, bucket: str, key: str) -> Path:
        """Resolve a bucket/key to a filesystem path."""
        safe_bucket = bucket.replace("/", "_").replace("\\", "_")
        safe_key = key.replace("/", os.sep).replace("\\", os.sep)
        return self.base_path / safe_bucket / safe_key

    async def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> StorageUploadResult:
        """Upload an object to local storage.

        Args:
            bucket: Target bucket name (maps to a directory)
            key: Object key/path
            data: Object data as bytes
            content_type: MIME type (not used for local storage)

        Returns:
            Upload result
        """
        file_path = self._resolve_path(bucket, key)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_bytes(data)

        etag = hashlib.md5(data).hexdigest()

        logger.info(
            f"Uploaded object to local storage: {bucket}/{key} ({len(data)} bytes)"
        )

        return StorageUploadResult(
            key=key,
            bucket=bucket,
            size=len(data),
            etag=etag,
            url=str(file_path),
        )

    async def download(self, bucket: str, key: str) -> bytes:
        """Download an object from local storage.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            Object data as bytes

        Raises:
            StorageError: If the object does not exist
        """
        file_path = self._resolve_path(bucket, key)

        if not file_path.exists():
            raise StorageError(
                f"Object not found: {bucket}/{key}",
                provider_error_code="not_found",
            )

        return file_path.read_bytes()

    async def delete(self, bucket: str, key: str) -> bool:
        """Delete an object from local storage.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            True if the object was deleted
        """
        file_path = self._resolve_path(bucket, key)

        if not file_path.exists():
            return False

        file_path.unlink()
        logger.info(f"Deleted object from local storage: {bucket}/{key}")
        return True

    async def exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in local storage.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            True if the object exists
        """
        file_path = self._resolve_path(bucket, key)
        return file_path.exists()

    async def get_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Get a file:// URL for a local object.

        Args:
            bucket: Bucket name
            key: Object key/path
            expires_in: Ignored for local storage

        Returns:
            file:// URL string
        """
        file_path = self._resolve_path(bucket, key)
        return f"file://{file_path}"


__all__ = ["LocalStorageProvider"]
