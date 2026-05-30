from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.dashboard.models import (
    DashboardMetricProjection,
    DashboardProjectionEvent,
    DashboardSlaTargetProjection,
)
from app.domains.insurance.models import (
    InsuranceAppointment,
    InsuranceConversation,
    InsuranceEmployeeAssignment,
    InsuranceIncidentReport,
    InsuranceMessage,
    InsurancePolicy,
)
from app.domains.shared.models import DomainOutboxEvent


class DashboardProjectionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def apply_event(self, event: DomainOutboxEvent) -> bool:
        if await self._was_applied(event):
            return False

        payload = event.payload_json
        if event.event_type == "IncidentReported":
            await self._increment(event.organization_id, "claim_states", "reported")
            await self._upsert_target(event, "claim", "reported")
        elif event.event_type == "ClaimTransitioned":
            await self._increment(
                event.organization_id, "claim_states", payload["from_state"], -1
            )
            await self._increment(
                event.organization_id, "claim_states", payload["to_state"]
            )
            await self._upsert_target(event, "claim", payload["to_state"])
        elif event.event_type == "PolicyActivated":
            await self._increment(event.organization_id, "policies", "active")
        elif event.event_type == "CustomerAssigned":
            await self._upsert_target(
                event, "assignment", payload.get("status", "active")
            )
        elif event.event_type == "AppointmentRequested":
            await self._increment(event.organization_id, "appointments", "requested")
            await self._upsert_target(event, "appointment", "requested")
        elif event.event_type == "SupportConversationStarted":
            await self._increment(
                event.organization_id, "support_activity", "open_conversations"
            )
            await self._upsert_target(event, "conversation", "open")
        elif event.event_type == "SupportMessageSent":
            await self._increment(event.organization_id, "support_activity", "messages")

        self.session.add(
            DashboardProjectionEvent(
                id=new_id("dashboard_event"),
                organization_id=event.organization_id,
                event_id=event.id,
                event_type=event.event_type,
            )
        )
        await self.session.flush()
        return True

    async def reconcile(self, organization_id: str) -> None:
        await self.session.execute(
            delete(DashboardMetricProjection).where(
                DashboardMetricProjection.organization_id == organization_id
            )
        )
        await self.session.execute(
            delete(DashboardSlaTargetProjection).where(
                DashboardSlaTargetProjection.organization_id == organization_id
            )
        )
        for state, value in await self._source_counts(
            InsuranceIncidentReport, InsuranceIncidentReport.claim_state, organization_id
        ):
            await self._increment(organization_id, "claim_states", state, value)
        active_policies = await self._source_matching_count(
            InsurancePolicy,
            organization_id,
            InsurancePolicy.status == "active",
        )
        await self._increment(organization_id, "policies", "active", active_policies)
        open_conversations = await self._source_matching_count(
            InsuranceConversation,
            organization_id,
            InsuranceConversation.status == "open",
        )
        await self._increment(
            organization_id,
            "support_activity",
            "open_conversations",
            open_conversations,
        )
        messages = await self._source_matching_count(InsuranceMessage, organization_id)
        await self._increment(organization_id, "support_activity", "messages", messages)
        requested_appointments = await self._source_matching_count(
            InsuranceAppointment,
            organization_id,
            InsuranceAppointment.status == "requested",
        )
        await self._increment(
            organization_id, "appointments", "requested", requested_appointments
        )
        for target_type, model in {
            "assignment": InsuranceEmployeeAssignment,
            "claim": InsuranceIncidentReport,
            "appointment": InsuranceAppointment,
            "conversation": InsuranceConversation,
        }.items():
            result = await self.session.scalars(
                select(model).where(model.organization_id == organization_id)
            )
            for item in result.all():
                self.session.add(
                    DashboardSlaTargetProjection(
                        id=new_id("dashboard_target"),
                        organization_id=organization_id,
                        target_type=target_type,
                        target_id=item.id,
                        status=item.status,
                        due_at=item.due_at,
                        last_event_id="reconciliation",
                    )
                )
        await self.session.commit()

    async def read_dimensions(self, organization_id: str, metric_key: str) -> dict[str, int]:
        result = await self.session.execute(
            select(DashboardMetricProjection.dimension, DashboardMetricProjection.value)
            .where(
                DashboardMetricProjection.organization_id == organization_id,
                DashboardMetricProjection.metric_key == metric_key,
                DashboardMetricProjection.time_bucket == "all",
            )
            .order_by(DashboardMetricProjection.dimension.asc())
        )
        return {str(dimension): int(value) for dimension, value in result.all()}

    async def read_value(
        self, organization_id: str, metric_key: str, dimension: str
    ) -> int:
        value = await self.session.scalar(
            select(DashboardMetricProjection.value).where(
                DashboardMetricProjection.organization_id == organization_id,
                DashboardMetricProjection.metric_key == metric_key,
                DashboardMetricProjection.dimension == dimension,
                DashboardMetricProjection.time_bucket == "all",
            )
        )
        return int(value or 0)

    async def _was_applied(self, event: DomainOutboxEvent) -> bool:
        return (
            await self.session.scalar(
                select(DashboardProjectionEvent.id).where(
                    DashboardProjectionEvent.organization_id == event.organization_id,
                    DashboardProjectionEvent.event_id == event.id,
                )
            )
            is not None
        )

    async def _increment(
        self,
        organization_id: str,
        metric_key: str,
        dimension: str,
        delta: int = 1,
    ) -> None:
        if delta == 0:
            return
        metric = await self.session.scalar(
            select(DashboardMetricProjection)
            .where(
                DashboardMetricProjection.organization_id == organization_id,
                DashboardMetricProjection.metric_key == metric_key,
                DashboardMetricProjection.dimension == dimension,
                DashboardMetricProjection.time_bucket == "all",
            )
            .with_for_update()
        )
        if metric is None:
            metric = DashboardMetricProjection(
                id=new_id("dashboard_metric"),
                organization_id=organization_id,
                metric_key=metric_key,
                dimension=dimension,
                time_bucket="all",
                value=0,
            )
            self.session.add(metric)
        metric.value = max(0, metric.value + delta)

    async def _upsert_target(
        self, event: DomainOutboxEvent, target_type: str, status: str
    ) -> None:
        target = await self.session.scalar(
            select(DashboardSlaTargetProjection)
            .where(
                DashboardSlaTargetProjection.organization_id == event.organization_id,
                DashboardSlaTargetProjection.target_type == target_type,
                DashboardSlaTargetProjection.target_id == event.aggregate_id,
            )
            .with_for_update()
        )
        if target is None:
            target = DashboardSlaTargetProjection(
                id=new_id("dashboard_target"),
                organization_id=event.organization_id,
                target_type=target_type,
                target_id=event.aggregate_id,
                status=status,
                last_event_id=event.id,
            )
            self.session.add(target)
        else:
            target.status = status
            target.last_event_id = event.id

    async def _source_counts(self, model: type, column, organization_id: str):
        result = await self.session.execute(
            select(column, func.count())
            .select_from(model)
            .where(model.organization_id == organization_id)
            .group_by(column)
        )
        return result.all()

    async def _source_matching_count(
        self, model: type, organization_id: str, *conditions
    ) -> int:
        value = await self.session.scalar(
            select(func.count())
            .select_from(model)
            .where(model.organization_id == organization_id, *conditions)
        )
        return int(value or 0)
