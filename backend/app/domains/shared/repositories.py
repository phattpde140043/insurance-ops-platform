from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.domains.shared.models import (
    BackgroundJob,
    DomainOutboxEvent,
    FileAsset,
    IdempotencyRecord,
    ExportArtifact,
)


class FileAssetRepository(BaseRepository[FileAsset]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FileAsset)


class BackgroundJobRepository(BaseRepository[BackgroundJob]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BackgroundJob)

    async def claim_next_batch(
        self,
        *,
        worker_id: str,
        now: datetime,
        locked_until: datetime,
        batch_size: int,
    ) -> list[BackgroundJob]:
        result = await self.session.scalars(
            select(BackgroundJob)
            .where(
                or_(
                    and_(
                        BackgroundJob.status == "queued",
                        BackgroundJob.available_at <= now,
                    ),
                    and_(
                        BackgroundJob.status == "processing",
                        BackgroundJob.locked_until < now,
                    ),
                )
            )
            .order_by(BackgroundJob.available_at.asc(), BackgroundJob.created_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        jobs = list(result.all())
        for job in jobs:
            job.status = "processing"
            job.locked_by = worker_id
            job.locked_until = locked_until
            job.started_at = now
            job.finished_at = None
            job.attempts += 1
        await self.session.flush()
        return jobs


class DomainOutboxEventRepository(BaseRepository[DomainOutboxEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DomainOutboxEvent)

    async def claim_next_batch(
        self,
        *,
        worker_id: str,
        now: datetime,
        locked_until: datetime,
        batch_size: int,
    ) -> list[DomainOutboxEvent]:
        result = await self.session.scalars(
            select(DomainOutboxEvent)
            .where(
                or_(
                    and_(
                        DomainOutboxEvent.status == "pending",
                        DomainOutboxEvent.available_at <= now,
                    ),
                    and_(
                        DomainOutboxEvent.status == "processing",
                        DomainOutboxEvent.locked_until < now,
                    ),
                )
            )
            .order_by(
                DomainOutboxEvent.available_at.asc(),
                DomainOutboxEvent.created_at.asc(),
            )
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        events = list(result.all())
        for event in events:
            event.status = "processing"
            event.locked_by = worker_id
            event.locked_until = locked_until
            event.attempts += 1
        await self.session.flush()
        return events


class IdempotencyRecordRepository(BaseRepository[IdempotencyRecord]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, IdempotencyRecord)

    async def get_for_command(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        command_name: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None:
        return await self.session.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.organization_id == organization_id,
                IdempotencyRecord.actor_user_id == actor_user_id,
                IdempotencyRecord.command_name == command_name,
                IdempotencyRecord.idempotency_key == idempotency_key,
            )
        )


class ExportArtifactRepository(BaseRepository[ExportArtifact]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ExportArtifact)
