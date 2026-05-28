from datetime import UTC, datetime, timedelta

from app.domains.dashboard.sla_service import SlaStatusService


def test_sla_status_is_due_before_threshold() -> None:
    service = SlaStatusService()
    created_at = datetime(2026, 5, 28, 8, 0, tzinfo=UTC)

    result = service.classify_item(
        created_at=created_at,
        now=created_at + timedelta(minutes=29),
        threshold_minutes=30,
        workflow_status="open",
    )

    assert result == "due"


def test_sla_status_breaches_exactly_at_threshold() -> None:
    service = SlaStatusService()
    created_at = datetime(2026, 5, 28, 8, 0, tzinfo=UTC)

    result = service.classify_item(
        created_at=created_at,
        now=created_at + timedelta(minutes=30),
        threshold_minutes=30,
        workflow_status="open",
    )

    assert result == "breached"


def test_sla_status_resolves_for_closed_workflow_item() -> None:
    service = SlaStatusService()
    created_at = datetime(2026, 5, 28, 8, 0, tzinfo=UTC)

    result = service.classify_item(
        created_at=created_at,
        now=created_at + timedelta(days=2),
        threshold_minutes=30,
        workflow_status="closed",
    )

    assert result == "resolved"
