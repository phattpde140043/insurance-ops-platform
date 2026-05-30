import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.dashboard.sla_service import SlaEvaluationService
from app.domains.dashboard.projection_service import DashboardProjectionService
from app.domains.ai.knowledge_service import KnowledgeDocumentService
from app.domains.insurance.export_service import ClaimExportService
from app.domains.shared.job_service import BackgroundJobService, BackgroundJobType
from app.domains.shared.outbox_service import DomainEventDispatcher, DomainOutboxService


class BackgroundWorker:
    def __init__(
        self,
        session: AsyncSession,
        poll_interval_seconds: float = 2.0,
        worker_id: str | None = None,
    ) -> None:
        self.session = session
        self.job_service = BackgroundJobService(session)
        self.outbox = DomainOutboxService(session)
        projection_service = DashboardProjectionService(session)
        self.dispatcher = DomainEventDispatcher(
            {
                event_type: [projection_service.apply_event]
                for event_type in {
                    "AppointmentRequested",
                    "ClaimTransitioned",
                    "CustomerAssigned",
                    "IncidentReported",
                    "PolicyActivated",
                    "SupportConversationStarted",
                    "SupportMessageSent",
                }
            }
        )
        self.poll_interval_seconds = poll_interval_seconds
        self.worker_id = worker_id or f"worker-{uuid4().hex[:12]}"

    async def run_once(self) -> bool:
        if await self.run_outbox_once():
            return True
        jobs = await self.job_service.claim_next_batch(
            worker_id=self.worker_id,
            batch_size=1,
        )
        if not jobs:
            return False

        job = jobs[0]
        try:
            if job.job_type == BackgroundJobType.KNOWLEDGE_INGEST.value:
                await KnowledgeDocumentService(self.session).process_ingest_job(
                    organization_id=job.organization_id,
                    actor_user_id=job.payload.get("actor_user_id"),
                    document_id=job.payload["document_id"],
                    background_job_id=job.id,
                )
            elif job.job_type == BackgroundJobType.SLA_EVALUATE.value:
                service = SlaEvaluationService(self.session)
                await service.run_for_organization(organization_id=job.organization_id)
            elif job.job_type == BackgroundJobType.DASHBOARD_RECONCILE.value:
                await DashboardProjectionService(self.session).reconcile(
                    job.organization_id
                )
            elif job.job_type == BackgroundJobType.EXPORT_GENERATE.value:
                await ClaimExportService(self.session).process_export_job(
                    organization_id=job.organization_id,
                    artifact_id=job.payload["artifact_id"],
                )
            else:
                raise ValueError(f"Unsupported job type: {job.job_type}")

            await self.job_service.mark_completed(
                organization_id=job.organization_id,
                actor_user_id=None,
                job_id=job.id,
            )
        except Exception as exc:
            await self.session.rollback()
            if job.job_type == BackgroundJobType.KNOWLEDGE_INGEST.value:
                document_id = job.payload.get("document_id")
                if document_id:
                    await KnowledgeDocumentService(self.session).mark_ingest_failed(
                        organization_id=job.organization_id,
                        document_id=document_id,
                    )
            await self.job_service.mark_failed(
                organization_id=job.organization_id,
                actor_user_id=None,
                job_id=job.id,
                error_message=str(exc),
            )
        return True

    async def run_outbox_once(self) -> bool:
        events = await self.outbox.claim_next_batch(
            worker_id=self.worker_id,
            batch_size=1,
        )
        if not events:
            return False
        event = events[0]
        try:
            await self.dispatcher.dispatch(event)
            await self.outbox.mark_published(event)
        except Exception as exc:
            await self.session.rollback()
            await self.outbox.mark_failed(event, str(exc))
        return True

    async def run_forever(self) -> None:
        while True:
            processed = await self.run_once()
            if not processed:
                await asyncio.sleep(self.poll_interval_seconds)
