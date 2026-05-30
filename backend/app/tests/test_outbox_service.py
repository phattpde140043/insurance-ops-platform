from datetime import UTC, datetime

import pytest

from app.domains.shared.models import DomainOutboxEvent
from app.domains.shared.outbox_service import DomainEventDispatcher, DomainOutboxService


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class FakeRepository:
    def __init__(self) -> None:
        self.events: list[DomainOutboxEvent] = []

    async def add(self, event: DomainOutboxEvent) -> DomainOutboxEvent:
        self.events.append(event)
        return event


def build_event(*, attempts: int = 1) -> DomainOutboxEvent:
    return DomainOutboxEvent(
        id="event_1",
        organization_id="org_demo",
        event_type="IncidentReported",
        aggregate_type="insurance_claim",
        aggregate_id="incident_1",
        producer_module="insurance",
        payload_json={},
        status="processing",
        attempts=attempts,
        available_at=datetime.now(UTC),
        locked_by="worker_1",
    )


@pytest.mark.asyncio
async def test_append_creates_pending_outbox_event() -> None:
    service = DomainOutboxService(FakeSession())  # type: ignore[arg-type]
    service.repository = FakeRepository()  # type: ignore[assignment]

    event = await service.append(
        organization_id="org_demo",
        event_type="IncidentReported",
        aggregate_type="insurance_claim",
        aggregate_id="incident_1",
        producer_module="insurance",
        payload={"claim_state": "reported"},
    )

    assert event.status == "pending"
    assert event.payload_json == {"claim_state": "reported"}


@pytest.mark.asyncio
async def test_mark_published_releases_lease() -> None:
    session = FakeSession()
    service = DomainOutboxService(session)  # type: ignore[arg-type]
    event = build_event()

    await service.mark_published(event)

    assert event.status == "published"
    assert event.locked_by is None
    assert event.published_at is not None
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_mark_failed_schedules_bounded_retry() -> None:
    session = FakeSession()
    service = DomainOutboxService(session)  # type: ignore[arg-type]
    event = build_event()

    await service.mark_failed(event, "temporary dispatch error")

    assert event.status == "pending"
    assert event.locked_by is None
    assert event.error_message == "temporary dispatch error"
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_dispatcher_calls_matching_consumers() -> None:
    dispatched: list[str] = []

    async def consume(event: DomainOutboxEvent) -> None:
        dispatched.append(event.id)

    await DomainEventDispatcher({"IncidentReported": [consume]}).dispatch(build_event())

    assert dispatched == ["event_1"]
