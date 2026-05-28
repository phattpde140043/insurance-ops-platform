from pathlib import Path
from typing import Protocol

from fastapi import HTTPException, status

from app.core.config import settings


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
}


class StorageProvider(Protocol):
    async def put_bytes(self, storage_key: str, content: bytes) -> None:
        """Store bytes by storage key."""

    async def get_bytes(self, storage_key: str) -> bytes:
        """Read bytes by storage key."""

    async def delete(self, storage_key: str) -> None:
        """Delete a stored object."""


class LocalStorageProvider:
    def __init__(self, root: str = settings.local_storage_root) -> None:
        self.root = Path(root)

    async def put_bytes(self, storage_key: str, content: bytes) -> None:
        path = self._resolve(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    async def get_bytes(self, storage_key: str) -> bytes:
        return self._resolve(storage_key).read_bytes()

    async def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        if path.exists():
            path.unlink()

    def _resolve(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        root = self.root.resolve()
        if root not in path.parents and path != root:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_storage_key",
                    "message": "Storage key resolves outside the configured storage root.",
                },
            )
        return path


def validate_upload(*, mime_type: str, size_bytes: int) -> None:
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "unsupported_file_type",
                "message": "Only PDF, JPG and PNG files are supported.",
            },
        )
    if size_bytes > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "file_too_large",
                "message": "Uploaded file exceeds the configured size limit.",
            },
        )

