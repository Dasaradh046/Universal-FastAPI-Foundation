"""
MinIO / S3-compatible storage provider.

Stores objects in any S3-compatible object store (AWS S3, MinIO, etc.)
using boto3. Synchronous boto3 calls are run in a thread executor for
async compatibility.
"""

from __future__ import annotations

import asyncio
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.storage.contracts import (
    StorageError,
    StorageProvider,
    StorageUploadResult,
)

logger = get_logger(__name__)


class MinIOStorageProvider(StorageProvider):
    """MinIO / S3-compatible storage provider implementation."""

    def __init__(self):
        self.endpoint = settings.MINIO_ENDPOINT
        self.access_key = settings.MINIO_ACCESS_KEY
        self.secret_key = settings.MINIO_SECRET_KEY
        self.secure = settings.MINIO_SECURE

        if not self.access_key or not self.secret_key:
            raise ValueError("MINIO_ACCESS_KEY and MINIO_SECRET_KEY must be configured")

        scheme = "https" if self.secure else "http"
        self.endpoint_url = f"{scheme}://{self.endpoint}"

        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    async def _run(self, func, *args, **kwargs):
        """Run a synchronous boto3 call in a thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    async def _ensure_bucket(self, bucket: str) -> None:
        """Create the bucket if it doesn't exist."""

        def _create():
            try:
                self._client.head_bucket(Bucket=bucket)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    self._client.create_bucket(Bucket=bucket)
                else:
                    raise

        await self._run(_create)

    async def upload(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: Optional[str] = None,
    ) -> StorageUploadResult:
        """Upload an object to MinIO/S3.

        Args:
            bucket: Target bucket name
            key: Object key/path
            data: Object data as bytes
            content_type: MIME type of the object

        Returns:
            Upload result
        """
        await self._ensure_bucket(bucket)

        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type

        try:
            response = await self._run(
                self._client.put_object,
                Bucket=bucket,
                Key=key,
                Body=data,
                **extra_args,
            )
        except NoCredentialsError as e:
            raise StorageError(
                "MinIO/S3 credentials not found",
                provider_error_code="no_credentials",
            ) from e
        except ClientError as e:
            raise StorageError(
                f"MinIO/S3 upload failed: {e}",
                provider_error_code=e.response.get("Error", {}).get("Code", "unknown"),
            ) from e

        etag = response.get("ETag", "").strip('"')

        logger.info(f"Uploaded object to MinIO/S3: {bucket}/{key} ({len(data)} bytes)")

        return StorageUploadResult(
            key=key,
            bucket=bucket,
            size=len(data),
            etag=etag,
            url=f"{self.endpoint_url}/{bucket}/{key}",
        )

    async def download(self, bucket: str, key: str) -> bytes:
        """Download an object from MinIO/S3.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            Object data as bytes

        Raises:
            StorageError: If the object does not exist
        """
        try:
            response = await self._run(self._client.get_object, Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "unknown")
            if code == "NoSuchKey":
                raise StorageError(
                    f"Object not found: {bucket}/{key}",
                    provider_error_code="not_found",
                ) from e
            raise StorageError(
                f"MinIO/S3 download failed: {e}",
                provider_error_code=code,
            ) from e

    async def delete(self, bucket: str, key: str) -> bool:
        """Delete an object from MinIO/S3.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            True if the object was deleted
        """
        try:
            await self._run(self._client.delete_object, Bucket=bucket, Key=key)
            logger.info(f"Deleted object from MinIO/S3: {bucket}/{key}")
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "unknown")
            if code == "NoSuchKey":
                return False
            raise StorageError(
                f"MinIO/S3 delete failed: {e}",
                provider_error_code=code,
            ) from e

    async def exists(self, bucket: str, key: str) -> bool:
        """Check if an object exists in MinIO/S3.

        Args:
            bucket: Bucket name
            key: Object key/path

        Returns:
            True if the object exists
        """
        try:
            await self._run(self._client.head_object, Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "unknown")
            if code in ("404", "NoSuchKey"):
                return False
            raise StorageError(
                f"MinIO/S3 head_object failed: {e}",
                provider_error_code=code,
            ) from e

    async def get_url(
        self,
        bucket: str,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Get a presigned URL for a MinIO/S3 object.

        Args:
            bucket: Bucket name
            key: Object key/path
            expires_in: URL expiration in seconds

        Returns:
            Presigned URL string
        """
        try:
            url = await self._run(
                self._client.generate_presigned_url,
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise StorageError(
                f"MinIO/S3 presigned URL failed: {e}",
                provider_error_code=e.response.get("Error", {}).get("Code", "unknown"),
            ) from e


__all__ = ["MinIOStorageProvider"]
