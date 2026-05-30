import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings


ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/csv",
}


class StorageProvider(Protocol):
    async def put_bytes(self, storage_key: str, content: bytes) -> None:
        """Store bytes by storage key."""

    async def get_bytes(self, storage_key: str) -> bytes:
        """Read bytes by storage key."""

    async def delete(self, storage_key: str) -> None:
        """Delete a stored object."""

    async def create_download_url(
        self, storage_key: str, *, expires_seconds: int
    ) -> str | None:
        """Return a provider-native expiring URL, or None when proxying is required."""


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

    async def create_download_url(
        self, storage_key: str, *, expires_seconds: int
    ) -> str | None:
        self._resolve(storage_key)
        return None

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


class S3StorageProvider:
    def __init__(self, client: Any | None = None) -> None:
        if not settings.object_storage_bucket.strip():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "missing_object_storage_bucket",
                    "message": "Object storage bucket configuration is required.",
                },
            )
        self.bucket = settings.object_storage_bucket
        self.client = client or self._create_client()

    async def put_bytes(self, storage_key: str, content: bytes) -> None:
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket,
            Key=storage_key,
            Body=content,
        )

    async def get_bytes(self, storage_key: str) -> bytes:
        response = await asyncio.to_thread(
            self.client.get_object,
            Bucket=self.bucket,
            Key=storage_key,
        )
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, storage_key: str) -> None:
        await asyncio.to_thread(
            self.client.delete_object,
            Bucket=self.bucket,
            Key=storage_key,
        )

    async def create_download_url(
        self, storage_key: str, *, expires_seconds: int
    ) -> str | None:
        return await asyncio.to_thread(
            self.client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket, "Key": storage_key},
            ExpiresIn=expires_seconds,
        )

    def _create_client(self):
        import boto3

        return boto3.client(
            "s3",
            endpoint_url=settings.object_storage_endpoint_url,
            region_name=settings.object_storage_region,
            aws_access_key_id=settings.object_storage_access_key_id,
            aws_secret_access_key=settings.object_storage_secret_access_key,
        )


def get_storage_provider() -> StorageProvider:
    provider = settings.storage_provider.strip().lower()
    if provider == "local":
        return LocalStorageProvider()
    if provider == "s3":
        return S3StorageProvider()
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "invalid_storage_provider",
            "message": "Storage provider configuration is not recognized.",
        },
    )


def issue_storage_download_token(
    *, organization_id: str, storage_key: str, expires_seconds: int
) -> str:
    return jwt.encode(
        {
            "purpose": "storage_download",
            "org": organization_id,
            "storage_key": storage_key,
            "exp": datetime.now(UTC) + timedelta(seconds=expires_seconds),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def verify_storage_download_token(token: str) -> tuple[str, str]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_download_token",
                "message": "Download reference is invalid or expired.",
            },
        ) from exc
    organization_id = payload.get("org")
    storage_key = payload.get("storage_key")
    if (
        payload.get("purpose") != "storage_download"
        or not organization_id
        or not storage_key
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_download_token",
                "message": "Download reference is invalid or expired.",
            },
        )
    return organization_id, storage_key


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
