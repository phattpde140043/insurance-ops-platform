from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.insurance.models import (
    InsuranceAppointment,
    InsuranceConversation,
    InsuranceCustomer,
    InsuranceEmployeeAssignment,
    InsuranceIncidentReport,
    InsuranceMessage,
    InsurancePolicy,
)
from app.domains.platform.models import AuditEvent
from app.domains.dashboard.models import SlaAlert
from app.domains.dashboard.projection_service import DashboardProjectionService
from app.domains.shared.job_service import BackgroundJobService, BackgroundJobType


class DashboardAggregationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.projections = DashboardProjectionService(session)
        self.jobs = BackgroundJobService(session)

    async def get_summary(self, *, organization_id: str, role: str) -> dict:
        customers = await self._count(InsuranceCustomer, organization_id)
        policies = await self._count(InsurancePolicy, organization_id)
        incidents = await self._count(InsuranceIncidentReport, organization_id)
        audit_events = await self._count(AuditEvent, organization_id)
        claim_states = await self._projection_dimensions(organization_id, "claim_states")
        queue_status = await self._queue_status_counts(organization_id)
        overdue_work_items = await self._overdue_work_item_count(organization_id)
        support_activity = {
            "open_conversations": await self._projection_value(
                organization_id,
                "support_activity",
                "open_conversations",
            ),
            "messages": await self._projection_value(
                organization_id, "support_activity", "messages"
            ),
        }
        return {
            "role": role,
            "cards": [
                {"label": "Customers", "value": customers},
                {"label": "Policies", "value": policies},
                {"label": "Incidents", "value": incidents},
                {"label": "Audit Events", "value": audit_events},
            ],
            "next_build_steps": [
                "Add role-specific dashboard slices",
                "Add time-series chart endpoints",
                "Add frontend dashboard API integration",
            ],
            "metrics": {
                "claim_states": claim_states,
                "queue_status": queue_status,
                "overdue_work_items": overdue_work_items,
                "support_activity": support_activity,
                "active_policies": await self._projection_value(
                    organization_id, "policies", "active"
                ),
            },
        }

    async def get_role_dashboard(
        self, *, organization_id: str, role: str, focus: str
    ) -> dict:
        summary = await self.get_summary(organization_id=organization_id, role=role)
        summary["focus"] = focus
        return summary

    async def get_chart_series(self, *, organization_id: str) -> dict:
        claim_states = await self._projection_dimensions(organization_id, "claim_states")
        queue_status = await self._queue_status_counts(organization_id)
        return {
            "series": [
                {
                    "key": "claim_states",
                    "label": "Claims by state",
                    "data": self._chart_points(claim_states),
                },
                {
                    "key": "queue_status",
                    "label": "Queue by status",
                    "data": self._chart_points(queue_status),
                },
            ]
        }

    async def queue_reconciliation(
        self, *, organization_id: str, actor_user_id: str
    ) -> dict:
        job = await self.jobs.create_job(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            job_type=BackgroundJobType.DASHBOARD_RECONCILE.value,
            resource_type="dashboard_projection",
        )
        return {"status": "queued", "background_job_id": job.id}

    async def list_sla_alerts(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[dict]:
        conditions = [SlaAlert.organization_id == organization_id]
        if status:
            conditions.append(SlaAlert.status == status)
        result = await self.session.scalars(
            select(SlaAlert)
            .where(*conditions)
            .order_by(SlaAlert.breached_at.desc())
            .limit(min(max(limit, 1), 101))
            .offset(max(offset, 0))
        )
        return [self._serialize_alert(alert) for alert in result.all()]

    async def _count(self, model: type, organization_id: str) -> int:
        return await self._count_matching(model, organization_id)

    async def _projection_dimensions(
        self, organization_id: str, metric_key: str
    ) -> dict[str, int]:
        return await self.projections.read_dimensions(organization_id, metric_key)

    async def _projection_value(
        self, organization_id: str, metric_key: str, dimension: str
    ) -> int:
        return await self.projections.read_value(organization_id, metric_key, dimension)

    async def _count_matching(self, model: type, organization_id: str, *conditions) -> int:
        value = await self.session.scalar(
            select(func.count()).select_from(model).where(
                model.organization_id == organization_id,
                *conditions,
            )
        )
        return int(value or 0)

    async def _count_by_column(self, model: type, column, organization_id: str) -> dict:
        result = await self.session.execute(
            select(column, func.count())
            .select_from(model)
            .where(model.organization_id == organization_id)
            .group_by(column)
        )
        return {str(key): int(value) for key, value in result.all()}

    async def _queue_status_counts(self, organization_id: str) -> dict:
        counts: dict[str, int] = {}
        for model in (
            InsuranceEmployeeAssignment,
            InsuranceIncidentReport,
            InsuranceAppointment,
            InsuranceConversation,
        ):
            for status, value in (
                await self._count_by_column(model, model.status, organization_id)
            ).items():
                counts[status] = counts.get(status, 0) + value
        return counts

    async def _overdue_work_item_count(self, organization_id: str) -> int:
        now = datetime.now(UTC).isoformat()
        total = 0
        for model in (
            InsuranceEmployeeAssignment,
            InsuranceIncidentReport,
            InsuranceAppointment,
            InsuranceConversation,
        ):
            total += await self._count_matching(
                model,
                organization_id,
                model.due_at.is_not(None),
                model.due_at < now,
                model.status.not_in(("closed", "resolved", "done")),
            )
        return total

    def _chart_points(self, counts: dict) -> list[dict]:
        return [
            {"label": label, "value": value}
            for label, value in sorted(counts.items(), key=lambda item: item[0])
        ]

    def _serialize_alert(self, alert: SlaAlert) -> dict:
        return {
            "id": alert.id,
            "organization_id": alert.organization_id,
            "target_type": alert.target_type,
            "target_id": alert.target_id,
            "severity": alert.severity,
            "status": alert.status,
            "breached_at": alert.breached_at.isoformat() if alert.breached_at else "",
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        }
