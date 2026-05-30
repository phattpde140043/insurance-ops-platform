import pytest
from types import SimpleNamespace
from datetime import UTC, datetime

from app.domains.dashboard.service import DashboardAggregationService


@pytest.mark.asyncio
async def test_dashboard_summary_keeps_cards_and_adds_workflow_metrics() -> None:
    service = DashboardAggregationService.__new__(DashboardAggregationService)

    async def count(model, organization_id):
        return {
            "InsuranceCustomer": 2,
            "InsurancePolicy": 3,
            "InsuranceIncidentReport": 4,
            "AuditEvent": 5,
            "InsuranceMessage": 6,
        }.get(model.__name__, 0)

    async def count_by_column(_model, column, _organization_id):
        if column.name == "claim_state":
            return {"reported": 2, "closed": 1}
        return {"open": 1}

    async def queue_status_counts(_organization_id):
        return {"open": 3, "reported": 2}

    async def overdue_work_item_count(_organization_id):
        return 7

    async def count_matching(model, _organization_id, *conditions):
        if model.__name__ == "InsuranceConversation":
            return 8
        return await count(model, _organization_id)

    async def projection_dimensions(_organization_id, _metric_key):
        return {"reported": 2, "closed": 1}

    async def projection_value(_organization_id, metric_key, dimension):
        return {
            ("support_activity", "open_conversations"): 8,
            ("support_activity", "messages"): 6,
            ("policies", "active"): 3,
        }.get((metric_key, dimension), 0)

    service._count = count
    service._count_by_column = count_by_column
    service._queue_status_counts = queue_status_counts
    service._overdue_work_item_count = overdue_work_item_count
    service._count_matching = count_matching
    service._projection_dimensions = projection_dimensions
    service._projection_value = projection_value

    summary = await service.get_summary(organization_id="org_demo", role="admin")

    assert summary["cards"][0] == {"label": "Customers", "value": 2}
    assert summary["metrics"]["claim_states"] == {"reported": 2, "closed": 1}
    assert summary["metrics"]["queue_status"] == {"open": 3, "reported": 2}
    assert summary["metrics"]["overdue_work_items"] == 7
    assert summary["metrics"]["support_activity"] == {
        "open_conversations": 8,
        "messages": 6,
    }
    assert summary["metrics"]["active_policies"] == 3


@pytest.mark.asyncio
async def test_dashboard_summary_handles_empty_tenant_metrics() -> None:
    service = DashboardAggregationService.__new__(DashboardAggregationService)

    async def zero_count(_model, _organization_id):
        return 0

    async def empty_counts(_model, _column, _organization_id):
        return {}

    async def empty_queue(_organization_id):
        return {}

    async def no_overdue(_organization_id):
        return 0

    async def zero_matching(_model, _organization_id, *conditions):
        return 0

    async def zero_projection_dimensions(_organization_id, _metric_key):
        return {}

    async def zero_projection_value(_organization_id, _metric_key, _dimension):
        return 0

    service._count = zero_count
    service._count_by_column = empty_counts
    service._queue_status_counts = empty_queue
    service._overdue_work_item_count = no_overdue
    service._count_matching = zero_matching
    service._projection_dimensions = zero_projection_dimensions
    service._projection_value = zero_projection_value

    summary = await service.get_summary(organization_id="org_empty", role="employee")

    assert all(card["value"] == 0 for card in summary["cards"])
    assert summary["metrics"]["claim_states"] == {}
    assert summary["metrics"]["queue_status"] == {}
    assert summary["metrics"]["overdue_work_items"] == 0


@pytest.mark.asyncio
async def test_dashboard_chart_series_is_chart_ready() -> None:
    service = DashboardAggregationService.__new__(DashboardAggregationService)

    async def projection_dimensions(_organization_id, _metric_key):
        return {"triage": 2, "reported": 1}

    async def queue_status_counts(_organization_id):
        return {"open": 3}

    service._projection_dimensions = projection_dimensions
    service._queue_status_counts = queue_status_counts

    result = await service.get_chart_series(organization_id="org_demo")

    assert result["series"][0]["data"] == [
        {"label": "reported", "value": 1},
        {"label": "triage", "value": 2},
    ]
    assert result["series"][1]["data"] == [{"label": "open", "value": 3}]


def test_dashboard_alert_serializer_uses_compact_fields() -> None:
    service = DashboardAggregationService.__new__(DashboardAggregationService)
    breached_at = datetime(2026, 5, 28, 10, 0, tzinfo=UTC)
    alert = SimpleNamespace(
        id="alert_1",
        organization_id="org_demo",
        target_type="claim",
        target_id="incident_1",
        severity="warning",
        status="active",
        breached_at=breached_at,
        resolved_at=None,
    )

    result = service._serialize_alert(alert)

    assert result == {
        "id": "alert_1",
        "organization_id": "org_demo",
        "target_type": "claim",
        "target_id": "incident_1",
        "severity": "warning",
        "status": "active",
        "breached_at": breached_at.isoformat(),
        "resolved_at": None,
    }
