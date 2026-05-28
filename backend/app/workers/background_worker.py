import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.dashboard.sla_service import SlaEvaluationService
from app.domains.shared.job_service import BackgroundJobService, BackgroundJobType
from app.domains.shared.repositories import BackgroundJobRepository


class BackgroundWorker:
    def __init__(self, session: AsyncSession, poll_interval_seconds: float = 2.0) -> None:
        self.session = session
        self.jobs = BackgroundJobRepository(session)
        self.job_service = BackgroundJobService(session)
        self.poll_interval_seconds = poll_interval_seconds

    async def run_once(self) -> bool:
        job = await self.jobs.get_next_queued()
        if job is None:
            return False

        await self.job_service.mark_processing(job.organization_id, job.id)
        try:
            if job.job_type == BackgroundJobType.KNOWLEDGE_INGEST.value:
                pass
            elif job.job_type == BackgroundJobType.SLA_EVALUATE.value:
                service = SlaEvaluationService(self.session)
                await service.run_for_organization(organization_id=job.organization_id)
            else:
                raise ValueError(f"Unsupported job type: {job.job_type}")

            await self.job_service.mark_completed(
                organization_id=job.organization_id,
                actor_user_id=None,
                job_id=job.id,
            )
        except Exception as exc:
            await self.job_service.mark_failed(
                organization_id=job.organization_id,
                actor_user_id=None,
                job_id=job.id,
                error_message=str(exc),
            )
        return True

    async def run_forever(self) -> None:
        while True:
            processed = await self.run_once()
            if not processed:
                await asyncio.sleep(self.poll_interval_seconds)
