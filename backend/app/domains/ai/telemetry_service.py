from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_ai_pool_status
from app.domains.ai.models import AiProviderCall
from app.domains.shared.models import BackgroundJob


class AiOperationalTelemetryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_summary(self, *, organization_id: str) -> dict:
        queue_depth = await self.session.scalar(
            select(func.count())
            .select_from(BackgroundJob)
            .where(
                BackgroundJob.organization_id == organization_id,
                BackgroundJob.job_type == "knowledge_ingest",
                BackgroundJob.status.in_(("queued", "processing")),
            )
        )
        metrics = await self.session.execute(
            select(
                func.count(),
                func.coalesce(func.avg(AiProviderCall.latency_ms), 0),
                func.coalesce(
                    func.sum(case((AiProviderCall.status == "timeout", 1), else_=0)),
                    0,
                ),
            ).where(AiProviderCall.organization_id == organization_id)
        )
        provider_calls, average_latency_ms, timeout_count = metrics.one()
        pool = get_ai_pool_status()
        return {
            "queue_depth": int(queue_depth or 0),
            "worker_concurrency_limit": settings.ai_worker_concurrency,
            "provider_calls": int(provider_calls or 0),
            "average_provider_latency_ms": int(average_latency_ms or 0),
            "provider_timeout_count": int(timeout_count or 0),
            "pool": {
                **pool,
                "saturated": pool["checked_out"]
                >= settings.ai_database_pool_size
                + settings.ai_database_max_overflow,
            },
        }
