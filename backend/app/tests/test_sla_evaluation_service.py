from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.domains.dashboard.sla_service import SlaEvaluationService


class FakeSlaEvaluationService(SlaEvaluationService):
    def __init__(self, rules, items, alerts) -> None:
        self.rules = rules
        self.items = items
        self.alerts = alerts
        self.committed = False
        super().__init__(session=None)

    async def _active_rules(self, organization_id: str):
        return [rule for rule in self.rules if rule.organization_id == organization_id]

    async def _workflow_items(self, organization_id: str, target_type: str):
        return [
            item
            for item in self.items
            if item.organization_id == organization_id and item.target_type == target_type
        ]

    async def _active_alerts(self, organization_id: str, target_type: str):
        return [
            alert
            for alert in self.alerts
            if alert.organization_id == organization_id
            and alert.target_type == target_type
            and alert.status == "active"
        ]

    async def _add_alert(self, *, organization_id: str, rule, item, now: datetime) -> None:
        self.alerts.append(
            SimpleNamespace(
                id=f"alert_{item.id}",
                organization_id=organization_id,
                rule_id=rule.id,
                target_type=rule.target_type,
                target_id=item.id,
                severity=rule.severity,
                status="active",
                breached_at=now,
                resolved_at=None,
            )
        )

    async def _commit(self) -> None:
        self.committed = True


def build_rule():
    return SimpleNamespace(
        id="rule_claim",
        organization_id="org_demo",
        target_type="claim",
        threshold_minutes=30,
        severity="warning",
        status="active",
    )


def build_item(item_id: str, status: str, created_at: datetime):
    return SimpleNamespace(
        id=item_id,
        organization_id="org_demo",
        target_type="claim",
        status=status,
        created_at=created_at,
    )


@pytest.mark.asyncio
async def test_sla_evaluation_creates_active_alert_once() -> None:
    now = datetime(2026, 5, 28, 10, 0, tzinfo=UTC)
    service = FakeSlaEvaluationService(
        [build_rule()],
        [build_item("incident_1", "open", now - timedelta(hours=1))],
        [],
    )

    first = await service.run_for_organization(organization_id="org_demo", now=now)
    second = await service.run_for_organization(organization_id="org_demo", now=now)

    assert first["created"] == 1
    assert second["created"] == 0
    assert len(service.alerts) == 1
    assert service.committed


@pytest.mark.asyncio
async def test_sla_evaluation_resolves_alert_for_closed_item() -> None:
    now = datetime(2026, 5, 28, 10, 0, tzinfo=UTC)
    alert = SimpleNamespace(
        id="alert_1",
        organization_id="org_demo",
        target_type="claim",
        target_id="incident_1",
        status="active",
        resolved_at=None,
    )
    service = FakeSlaEvaluationService(
        [build_rule()],
        [build_item("incident_1", "closed", now - timedelta(hours=1))],
        [alert],
    )

    result = await service.run_for_organization(organization_id="org_demo", now=now)

    assert result["resolved"] == 1
    assert alert.status == "resolved"
    assert alert.resolved_at == now
