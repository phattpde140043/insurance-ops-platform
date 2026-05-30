from enum import StrEnum
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.core.config import settings
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService
from app.domains.shared.models import BackgroundJob
from app.domains.shared.repositories import BackgroundJobRepository


class BackgroundJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    POISONED = "poisoned"


class BackgroundJobType(StrEnum):
    KNOWLEDGE_INGEST = "knowledge_ingest"
    SLA_EVALUATE = "sla_evaluate"
    DASHBOARD_RECONCILE = "dashboard_reconcile"
    EXPORT_GENERATE = "export_generate"


class BackgroundJobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BackgroundJobRepository(session)
        self.audit_log = AuditLogService(session)

    async def create_job(
        self,
        *,
        organization_id: str,
        actor_user_id: str | None,
        job_type: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> BackgroundJob:
        job = BackgroundJob(
            id=new_id("job"),
            organization_id=organization_id,
            job_type=job_type,
            status=BackgroundJobStatus.QUEUED.value,
            resource_type=resource_type,
            resource_id=resource_id,
            attempts=0,
            payload=payload or {},
            available_at=datetime.now(UTC),
        )
        await self.repository.add(job)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="background_job.created",
                resource_type="background_job",
                resource_id=job.id,
                metadata={
                    "job_type": job_type,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                },
            )
        )
        await self.session.commit()
        return job

    async def claim_next_batch(
        self, *, worker_id: str, batch_size: int | None = None
    ) -> list[BackgroundJob]:
        now = datetime.now(UTC)
        jobs = await self.repository.claim_next_batch(
            worker_id=worker_id,
            now=now,
            locked_until=now + timedelta(seconds=settings.worker_lock_seconds),
            batch_size=min(max(batch_size or settings.worker_batch_size, 1), 100),
        )
        await self.session.commit()
        return jobs

    async def mark_completed(
        self, *, organization_id: str, actor_user_id: str | None, job_id: str
    ) -> BackgroundJob:
        job = await self._get_job(organization_id, job_id)
        job.status = BackgroundJobStatus.COMPLETED.value
        job.locked_by = None
        job.locked_until = None
        job.finished_at = datetime.now(UTC)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="background_job.completed",
                resource_type="background_job",
                resource_id=job.id,
            )
        )
        await self.session.commit()
        return job

    async def mark_failed(
        self,
        *,
        organization_id: str,
        actor_user_id: str | None,
        job_id: str,
        error_message: str,
    ) -> BackgroundJob:
        job = await self._get_job(organization_id, job_id)
        poisoned = job.attempts >= settings.worker_max_attempts
        job.status = (
            BackgroundJobStatus.POISONED.value
            if poisoned
            else BackgroundJobStatus.QUEUED.value
        )
        job.error_message = error_message[:500]
        job.locked_by = None
        job.locked_until = None
        job.finished_at = datetime.now(UTC) if poisoned else None
        if not poisoned:
            job.available_at = datetime.now(UTC) + timedelta(
                seconds=settings.worker_retry_backoff_seconds
            )
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action=(
                    "background_job.poisoned"
                    if poisoned
                    else "background_job.retry_scheduled"
                ),
                resource_type="background_job",
                resource_id=job.id,
                metadata={"attempts": job.attempts, "status": job.status},
            )
        )
        await self.session.commit()
        return job

    async def _get_job(self, organization_id: str, job_id: str) -> BackgroundJob:
        job = await self.repository.get_for_org(organization_id, job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "background_job_not_found",
                    "message": "Background job was not found.",
                },
            )
        return job
