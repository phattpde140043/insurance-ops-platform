from enum import StrEnum
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService
from app.domains.shared.models import BackgroundJob
from app.domains.shared.repositories import BackgroundJobRepository


class BackgroundJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundJobType(StrEnum):
    KNOWLEDGE_INGEST = "knowledge_ingest"
    SLA_EVALUATE = "sla_evaluate"


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

    async def mark_processing(self, organization_id: str, job_id: str) -> BackgroundJob:
        job = await self._get_job(organization_id, job_id)
        job.status = BackgroundJobStatus.PROCESSING.value
        job.attempts += 1
        await self.session.commit()
        return job

    async def mark_completed(
        self, *, organization_id: str, actor_user_id: str | None, job_id: str
    ) -> BackgroundJob:
        job = await self._get_job(organization_id, job_id)
        job.status = BackgroundJobStatus.COMPLETED.value
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
        job.status = BackgroundJobStatus.FAILED.value
        job.error_message = error_message
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="background_job.failed",
                resource_type="background_job",
                resource_id=job.id,
                metadata={"error_message": error_message},
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
