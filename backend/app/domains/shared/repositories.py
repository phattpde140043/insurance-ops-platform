from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.domains.shared.models import BackgroundJob, FileAsset


class FileAssetRepository(BaseRepository[FileAsset]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FileAsset)


class BackgroundJobRepository(BaseRepository[BackgroundJob]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BackgroundJob)

    async def get_next_queued(self) -> BackgroundJob | None:
        return await self.session.scalar(
            select(BackgroundJob)
            .where(BackgroundJob.status == "queued")
            .order_by(BackgroundJob.created_at.asc())
            .limit(1)
        )
