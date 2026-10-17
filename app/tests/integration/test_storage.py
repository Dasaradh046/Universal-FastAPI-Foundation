"""
Tests for the storage provider adapters.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.integrations.storage.contracts import (
    StorageError,
    StorageUploadResult,
)
from app.integrations.storage.providers.local import LocalStorageProvider


@pytest.fixture
def local_provider(tmp_path):
    """Create a LocalStorageProvider using a temp directory."""
    with patch("app.integrations.storage.providers.local.settings") as mock_settings:
        mock_settings.LOCAL_STORAGE_PATH = str(tmp_path / "storage")
        return LocalStorageProvider()


class TestLocalStorageProvider:
    """Tests for the LocalStorageProvider."""

    def test_upload_and_download(self, local_provider, tmp_path):
        """Uploading then downloading returns the same data."""
        import asyncio

        data = b"Hello, World!"

        result = asyncio.run(
            local_provider.upload("my-bucket", "hello.txt", data, "text/plain")
        )

        assert result.key == "hello.txt"
        assert result.bucket == "my-bucket"
        assert result.size == len(data)
        assert result.etag is not None

        downloaded = asyncio.run(local_provider.download("my-bucket", "hello.txt"))
        assert downloaded == data

    def test_upload_creates_directories(self, local_provider, tmp_path):
        """Upload creates bucket subdirectories as needed."""
        import asyncio

        data = b"nested data"

        asyncio.run(local_provider.upload("bucket-1", "a/b/c/nested.txt", data))

        expected_file = (
            tmp_path / "storage" / "bucket-1" / "a" / "b" / "c" / "nested.txt"
        )
        assert expected_file.exists()
        assert expected_file.read_bytes() == data

    def test_download_missing_raises(self, local_provider):
        """Downloading a missing object raises StorageError."""
        import asyncio

        with pytest.raises(StorageError, match="not found"):
            asyncio.run(local_provider.download("bucket", "missing.txt"))

    def test_delete_existing(self, local_provider):
        """Deleting an existing object returns True."""
        import asyncio

        data = b"to be deleted"
        asyncio.run(local_provider.upload("bucket", "temp.txt", data))

        result = asyncio.run(local_provider.delete("bucket", "temp.txt"))
        assert result is True

    def test_delete_missing_returns_false(self, local_provider):
        """Deleting a missing object returns False."""
        import asyncio

        result = asyncio.run(local_provider.delete("bucket", "missing.txt"))
        assert result is False

    def test_exists(self, local_provider):
        """exists returns True for existing objects, False otherwise."""
        import asyncio

        assert asyncio.run(local_provider.exists("bucket", "missing.txt")) is False

        asyncio.run(local_provider.upload("bucket", "present.txt", b"data"))

        assert asyncio.run(local_provider.exists("bucket", "present.txt")) is True

    def test_get_url(self, local_provider):
        """get_url returns a file:// URL."""
        import asyncio

        url = asyncio.run(local_provider.get_url("bucket", "key.txt"))
        assert url.startswith("file://")


class TestStorageContracts:
    """Tests for the storage data contracts."""

    def test_storage_upload_result(self):
        """StorageUploadResult can be created with required fields."""
        result = StorageUploadResult(
            key="test.txt",
            bucket="my-bucket",
            size=100,
        )
        assert result.key == "test.txt"
        assert result.bucket == "my-bucket"
        assert result.size == 100

    def test_storage_error(self):
        """StorageError can carry a provider error code."""
        err = StorageError("failed", provider_error_code="access_denied")
        assert str(err) == "failed"
        assert err.provider_error_code == "access_denied"
