from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.core.storage import StorageProvider, validate_upload
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
            status="stored",
            created_by_user_id=payload.created_by_user_id,
        )
        return await self.repository.add(asset)

