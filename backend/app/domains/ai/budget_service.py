from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.model_mixins import new_id
from app.domains.ai.models import AiProviderCall, AiRateLimitWindow
from app.domains.ai.repositories import (
    AiProviderCallRepository,
    AiRateLimitWindowRepository,
)
from app.domains.shared.models import BackgroundJob


class AiBudgetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.windows = AiRateLimitWindowRepository(session)
        self.provider_calls = AiProviderCallRepository(session)

    async def consume(
        self, *, organization_id: str, user_id: str, capability: str
    ) -> None:
        window_started_at = datetime.now(UTC).replace(second=0, microsecond=0)
        await self._increment_window(
            organization_id=organization_id,
            subject_type="user",
            subject_id=user_id,
            capability=capability,
            window_started_at=window_started_at,
            limit=settings.ai_user_requests_per_minute,
        )
        await self._increment_window(
            organization_id=organization_id,
            subject_type="tenant",
            subject_id=organization_id,
            capability=capability,
            window_started_at=window_started_at,
            limit=settings.ai_tenant_requests_per_minute,
        )
        await self.session.flush()

    async def ensure_ingest_capacity(self, *, organization_id: str) -> None:
        value = await self.session.scalar(
            select(func.count())
            .select_from(BackgroundJob)
            .where(
                BackgroundJob.organization_id == organization_id,
                BackgroundJob.job_type == "knowledge_ingest",
                BackgroundJob.status.in_(("queued", "processing")),
            )
        )
        capacity = min(
            settings.ai_max_concurrent_ingest_jobs,
            settings.ai_worker_concurrency,
        )
        if int(value or 0) >= capacity:
            self._raise_limit("AI ingestion capacity is currently exhausted.")

    async def record_provider_call(
        self,
        *,
        organization_id: str,
        capability: str,
        status_value: str,
        latency_ms: int,
        cost_units: int,
        error_message: str | None = None,
    ) -> None:
        await self.provider_calls.add(
            AiProviderCall(
                id=new_id("ai_call"),
                organization_id=organization_id,
                provider="local-rag",
                capability=capability,
                status=status_value,
                latency_ms=latency_ms,
                cost_units=cost_units,
                request_metadata={"redacted": True},
                error_message=error_message[:200] if error_message else None,
            )
        )

    async def _increment_window(
        self,
        *,
        organization_id: str,
        subject_type: str,
        subject_id: str,
        capability: str,
        window_started_at: datetime,
        limit: int,
    ) -> None:
        window = await self.windows.get_window(
            organization_id=organization_id,
            subject_type=subject_type,
            subject_id=subject_id,
            capability=capability,
            window_started_at=window_started_at,
        )
        if window is None:
            window = AiRateLimitWindow(
                id=new_id("ai_limit"),
                organization_id=organization_id,
                subject_type=subject_type,
                subject_id=subject_id,
                capability=capability,
                window_started_at=window_started_at,
                request_count=0,
            )
            await self.windows.add(window)
        if window.request_count >= limit:
            self._raise_limit("AI request budget exceeded. Retry in the next minute.")
        window.request_count += 1

    def _raise_limit(self, message: str) -> None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "ai_budget_exceeded",
                "message": message,
                "retry_after_seconds": 60,
            },
        )
