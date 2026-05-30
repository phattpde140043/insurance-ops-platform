from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.model_mixins import new_id
from app.domains.shared.models import DomainOutboxEvent
from app.domains.shared.repositories import DomainOutboxEventRepository

EventConsumer = Callable[[DomainOutboxEvent], Awaitable[None]]


class DomainOutboxService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DomainOutboxEventRepository(session)

    async def append(
        self,
        *,
        organization_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        producer_module: str,
        payload: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> DomainOutboxEvent:
        event = DomainOutboxEvent(
            id=new_id("event"),
            organization_id=organization_id,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            producer_module=producer_module,
            payload_json=payload or {},
            idempotency_key=idempotency_key,
            status="pending",
            attempts=0,
            available_at=datetime.now(UTC),
        )
        return await self.repository.add(event)

    async def claim_next_batch(
        self, *, worker_id: str, batch_size: int | None = None
    ) -> list[DomainOutboxEvent]:
        now = datetime.now(UTC)
        events = await self.repository.claim_next_batch(
            worker_id=worker_id,
            now=now,
            locked_until=now + timedelta(seconds=settings.worker_lock_seconds),
            batch_size=min(max(batch_size or settings.worker_batch_size, 1), 100),
        )
        await self.session.commit()
        return events

    async def mark_published(self, event: DomainOutboxEvent) -> None:
        event.status = "published"
        event.locked_by = None
        event.locked_until = None
        event.published_at = datetime.now(UTC)
        await self.session.commit()

    async def mark_failed(self, event: DomainOutboxEvent, error_message: str) -> None:
        event.status = "failed" if event.attempts >= settings.worker_max_attempts else "pending"
        event.locked_by = None
        event.locked_until = None
        event.error_message = error_message[:500]
        if event.status == "pending":
            event.available_at = datetime.now(UTC) + timedelta(
                seconds=settings.worker_retry_backoff_seconds
            )
        await self.session.commit()


class DomainEventDispatcher:
    def __init__(self, consumers: dict[str, list[EventConsumer]] | None = None) -> None:
        self.consumers = consumers or {}

    async def dispatch(self, event: DomainOutboxEvent) -> None:
        for consumer in self.consumers.get(event.event_type, []):
            await consumer(event)
