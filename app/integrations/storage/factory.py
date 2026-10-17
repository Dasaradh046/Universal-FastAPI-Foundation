"""
Storage service factory.
"""

from app.core.config import settings
from app.integrations.storage.contracts import StorageProvider
from app.integrations.storage.providers.local import LocalStorageProvider
from app.integrations.storage.providers.minio import MinIOStorageProvider


def get_storage_provider() -> StorageProvider:
    """Factory function to get the configured storage provider.

    Returns:
        An instance of the configured storage provider

    Raises:
        ValueError: If the configured storage provider is not supported
    """
    provider = settings.STORAGE_PROVIDER

    if provider == "minio":
        return MinIOStorageProvider()
    elif provider == "s3":
        # S3 uses the same MinIO/S3-compatible provider via boto3
        return MinIOStorageProvider()
    elif provider == "local":
        return LocalStorageProvider()
    else:
        raise ValueError(f"Unsupported storage provider: {provider}")


__all__ = ["get_storage_provider"]
