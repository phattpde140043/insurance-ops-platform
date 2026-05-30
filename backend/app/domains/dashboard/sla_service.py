from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.dashboard.models import SlaAlert, SlaRule
from app.domains.dashboard.models import DashboardSlaTargetProjection
from app.domains.shared.outbox_service import DomainOutboxService


class SlaStatusService:
    def classify_item(
        self,
        *,
        created_at: datetime,
        now: datetime,
        threshold_minutes: int,
        workflow_status: str,
    ) -> str:
        if workflow_status in {"closed", "resolved", "done"}:
            return "resolved"
        threshold_at = created_at + timedelta(minutes=threshold_minutes)
        if now >= threshold_at:
            return "breached"
        return "due"


class SlaEvaluationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.status = SlaStatusService()
        self.outbox = DomainOutboxService(session)

    async def run_for_organization(
        self, *, organization_id: str, now: datetime | None = None
    ) -> dict:
        now = now or datetime.now(UTC)
        created = 0
        resolved = 0
        evaluated = 0
        rules = await self._active_rules(organization_id)
        for rule in rules:
            items = await self._workflow_items(organization_id, rule.target_type)
            alerts = await self._active_alerts(organization_id, rule.target_type)
            alerts_by_target = {alert.target_id: alert for alert in alerts}
            for item in items:
                evaluated += 1
                item_status = self.status.classify_item(
                    created_at=item.created_at,
                    now=now,
                    threshold_minutes=rule.threshold_minutes,
                    workflow_status=item.status,
                )
                existing_alert = alerts_by_target.get(item.id)
                if item_status == "breached" and existing_alert is None:
                    await self._add_alert(
                        organization_id=organization_id,
                        rule=rule,
                        item=item,
                        now=now,
                    )
                    created += 1
                elif item_status == "resolved" and existing_alert is not None:
                    await self._resolve_alert(existing_alert, now=now)
                    resolved += 1
        await self._commit()
        return {"evaluated": evaluated, "created": created, "resolved": resolved}

    async def _active_rules(self, organization_id: str) -> list[SlaRule]:
        result = await self.session.scalars(
            select(SlaRule).where(
                SlaRule.organization_id == organization_id,
                SlaRule.status == "active",
            )
        )
        return list(result.all())

    async def _workflow_items(self, organization_id: str, target_type: str) -> list:
        result = await self.session.scalars(
            select(DashboardSlaTargetProjection).where(
                DashboardSlaTargetProjection.organization_id == organization_id,
                DashboardSlaTargetProjection.target_type == target_type,
            )
        )
        return list(result.all())

    async def _active_alerts(
        self, organization_id: str, target_type: str
    ) -> list[SlaAlert]:
        result = await self.session.scalars(
            select(SlaAlert).where(
                SlaAlert.organization_id == organization_id,
                SlaAlert.target_type == target_type,
                SlaAlert.status == "active",
            )
        )
        return list(result.all())

    async def _add_alert(
        self, *, organization_id: str, rule: SlaRule, item, now: datetime
    ) -> None:
        alert = SlaAlert(
            id=new_id("sla_alert"),
            organization_id=organization_id,
            rule_id=rule.id,
            target_type=rule.target_type,
            target_id=item.id,
            severity=rule.severity,
            status="active",
            breached_at=now,
        )
        self.session.add(alert)
        await self._emit(
            organization_id=organization_id,
            event_type="SlaAlertRaised",
            aggregate_id=alert.id,
            payload={
                "target_type": rule.target_type,
                "target_id": item.id,
                "severity": rule.severity,
            },
        )

    async def _resolve_alert(self, alert: SlaAlert, *, now: datetime) -> None:
        alert.status = "resolved"
        alert.resolved_at = now
        await self._emit(
            organization_id=alert.organization_id,
            event_type="SlaAlertResolved",
            aggregate_id=alert.id,
            payload={
                "target_type": alert.target_type,
                "target_id": alert.target_id,
            },
        )

    async def _emit(
        self,
        *,
        organization_id: str,
        event_type: str,
        aggregate_id: str,
        payload: dict,
    ) -> None:
        if self.session is not None:
            await self.outbox.append(
                organization_id=organization_id,
                event_type=event_type,
                aggregate_type="sla_alert",
                aggregate_id=aggregate_id,
                producer_module="dashboard",
                payload=payload,
            )

    async def _commit(self) -> None:
        await self.session.commit()
