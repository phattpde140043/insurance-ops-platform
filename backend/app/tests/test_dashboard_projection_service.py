from datetime import UTC, datetime

import pytest

from app.domains.dashboard.models import DashboardProjectionEvent
from app.domains.dashboard.projection_service import DashboardProjectionService
from app.domains.shared.models import DomainOutboxEvent


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.flush_count = 0
        self.execute_count = 0
        self.commit_count = 0

    def add(self, record: object) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        self.flush_count += 1

    async def execute(self, _statement):
        self.execute_count += 1

    async def scalars(self, _statement):
        class EmptyResult:
            def all(self):
                return []

        return EmptyResult()

    async def commit(self) -> None:
        self.commit_count += 1


def build_event(event_type: str, payload: dict | None = None) -> DomainOutboxEvent:
    return DomainOutboxEvent(
        id="event_1",
        organization_id="org_demo",
        event_type=event_type,
        aggregate_type="insurance_claim",
        aggregate_id="incident_1",
        producer_module="insurance",
        payload_json=payload or {},
        status="processing",
        attempts=1,
        available_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_claim_transition_projection_updates_counters_and_target() -> None:
    service = DashboardProjectionService(FakeSession())  # type: ignore[arg-type]
    increments: list[tuple[str, str, int]] = []
    targets: list[tuple[str, str]] = []

    async def was_applied(_event) -> bool:
        return False

    async def increment(_organization_id, metric_key, dimension, delta=1) -> None:
        increments.append((metric_key, dimension, delta))

    async def upsert(_event, target_type, status) -> None:
        targets.append((target_type, status))

    service._was_applied = was_applied  # type: ignore[method-assign]
    service._increment = increment  # type: ignore[method-assign]
    service._upsert_target = upsert  # type: ignore[method-assign]

    applied = await service.apply_event(
        build_event(
            "ClaimTransitioned",
            {"from_state": "reported", "to_state": "triage"},
        )
    )

    assert applied is True
    assert increments == [
        ("claim_states", "reported", -1),
        ("claim_states", "triage", 1),
    ]
    assert targets == [("claim", "triage")]
    assert isinstance(service.session.added[0], DashboardProjectionEvent)


@pytest.mark.asyncio
async def test_duplicate_projection_event_is_ignored() -> None:
    service = DashboardProjectionService(FakeSession())  # type: ignore[arg-type]

    async def was_applied(_event) -> bool:
        return True

    service._was_applied = was_applied  # type: ignore[method-assign]

    assert await service.apply_event(build_event("IncidentReported")) is False
    assert service.session.added == []


@pytest.mark.asyncio
async def test_reconciliation_rebuilds_metrics_from_source_counts() -> None:
    session = FakeSession()
    service = DashboardProjectionService(session)  # type: ignore[arg-type]
    increments: list[tuple[str, str, int]] = []

    async def source_counts(_model, _column, _organization_id):
        return [("reported", 2), ("triage", 1)]

    async def source_matching_count(model, _organization_id, *_conditions):
        return {
            "InsurancePolicy": 3,
            "InsuranceConversation": 4,
            "InsuranceMessage": 5,
            "InsuranceAppointment": 6,
        }[model.__name__]

    async def increment(_organization_id, metric_key, dimension, delta=1) -> None:
        increments.append((metric_key, dimension, delta))

    service._source_counts = source_counts  # type: ignore[method-assign]
    service._source_matching_count = source_matching_count  # type: ignore[method-assign]
    service._increment = increment  # type: ignore[method-assign]

    await service.reconcile("org_demo")

    assert session.execute_count == 2
    assert session.commit_count == 1
    assert ("claim_states", "reported", 2) in increments
    assert ("policies", "active", 3) in increments
    assert ("support_activity", "open_conversations", 4) in increments
    assert ("support_activity", "messages", 5) in increments
    assert ("appointments", "requested", 6) in increments
