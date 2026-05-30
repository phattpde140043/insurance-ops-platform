from dataclasses import dataclass
from hashlib import sha256
from urllib.parse import quote

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.core.config import settings
from app.core.storage import (
    StorageProvider,
    issue_storage_download_token,
    validate_upload,
)
from app.domains.shared.models import FileAsset
from app.domains.shared.repositories import FileAssetRepository


@dataclass(frozen=True)
class FileUploadCreate:
    organization_id: str
    created_by_user_id: str
    original_name: str
    mime_type: str
    content: bytes


class FileService:
    def __init__(self, session: AsyncSession, storage: StorageProvider) -> None:
        self.repository = FileAssetRepository(session)
        self.storage = storage

    async def create_file_asset(self, payload: FileUploadCreate) -> FileAsset:
        size_bytes = len(payload.content)
        validate_upload(mime_type=payload.mime_type, size_bytes=size_bytes)

        file_id = new_id("file")
        storage_key = f"{payload.organization_id}/{file_id}/{payload.original_name}"
        await self.storage.put_bytes(storage_key, payload.content)

        asset = FileAsset(
            id=file_id,
            organization_id=payload.organization_id,
            original_name=payload.original_name,
            storage_key=storage_key,
            mime_type=payload.mime_type,
            size_bytes=size_bytes,
            checksum_sha256=sha256(payload.content).hexdigest(),
            status="stored",
            created_by_user_id=payload.created_by_user_id,
        )
        return await self.repository.add(asset)

    async def create_download_reference(
        self,
        *,
        organization_id: str,
        file_asset_id: str,
        proxy_path: str,
    ) -> dict:
        asset = await self.repository.get_for_org(organization_id, file_asset_id)
        if asset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "file_asset_not_found",
                    "message": "File asset was not found.",
                },
            )
        expires_seconds = settings.storage_download_expires_seconds
        provider_url = await self.storage.create_download_url(
            asset.storage_key,
            expires_seconds=expires_seconds,
        )
        if provider_url is not None:
            return {"download_url": provider_url, "expires_in": expires_seconds}
        token = issue_storage_download_token(
            organization_id=organization_id,
            storage_key=asset.storage_key,
            expires_seconds=expires_seconds,
        )
        return {
            "download_url": f"{proxy_path}?token={quote(token)}",
            "expires_in": expires_seconds,
        }
