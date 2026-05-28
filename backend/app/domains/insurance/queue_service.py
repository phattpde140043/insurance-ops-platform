from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.insurance.schemas import UpdateQueueItemIn
from app.domains.insurance.models import (
    InsuranceAppointment,
    InsuranceConversation,
    InsuranceEmployeeAssignment,
    InsuranceIncidentReport,
)
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService


class WorkloadQueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_employee(
        self,
        *,
        organization_id: str,
        employee_user_id: str,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        assignment_customer_ids = await self._assigned_customer_ids(
            organization_id, employee_user_id
        )
        items = await self._assignment_items(
            organization_id,
            employee_user_id=employee_user_id,
            status=status,
            priority=priority,
            limit=limit,
        )
        if assignment_customer_ids:
            items.extend(
                await self._incident_items(
                    organization_id,
                    customer_ids=assignment_customer_ids,
                    status=status,
                    priority=priority,
                    limit=limit,
                )
            )
        items.extend(
            await self._appointment_items(
                organization_id,
                employee_user_id=employee_user_id,
                status=status,
                priority=priority,
                limit=limit,
            )
        )
        items.extend(
            await self._conversation_items(
                organization_id,
                employee_user_id=employee_user_id,
                status=status,
                priority=priority,
                limit=limit,
            )
        )
        return self._sort_items(items)[:limit]

    async def list_for_admin(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        items = await self._assignment_items(
            organization_id, status=status, priority=priority, limit=limit
        )
        items.extend(
            await self._incident_items(
                organization_id, status=status, priority=priority, limit=limit
            )
        )
        items.extend(
            await self._appointment_items(
                organization_id, status=status, priority=priority, limit=limit
            )
        )
        items.extend(
            await self._conversation_items(
                organization_id, status=status, priority=priority, limit=limit
            )
        )
        return self._sort_items(items)[:limit]

    async def _assigned_customer_ids(
        self, organization_id: str, employee_user_id: str
    ) -> set[str]:
        result = await self.session.scalars(
            select(InsuranceEmployeeAssignment.customer_id).where(
                InsuranceEmployeeAssignment.organization_id == organization_id,
                InsuranceEmployeeAssignment.employee_user_id == employee_user_id,
                InsuranceEmployeeAssignment.status == "active",
            )
        )
        return set(result.all())

    async def _assignment_items(
        self,
        organization_id: str,
        *,
        employee_user_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        limit: int,
    ) -> list[dict]:
        conditions = [InsuranceEmployeeAssignment.organization_id == organization_id]
        if employee_user_id is not None:
            conditions.append(
                InsuranceEmployeeAssignment.employee_user_id == employee_user_id
            )
        statement = self._apply_common_filters(
            select(InsuranceEmployeeAssignment).where(*conditions),
            InsuranceEmployeeAssignment,
            status,
            priority,
            limit,
        )
        result = await self.session.scalars(statement)
        return [
            self._queue_item(
                item_type="assignment",
                source_id=assignment.id,
                organization_id=assignment.organization_id,
                customer_id=assignment.customer_id,
                employee_user_id=assignment.employee_user_id,
                status=assignment.status,
                priority=assignment.priority,
                due_at=assignment.due_at,
                created_at=assignment.created_at.isoformat()
                if assignment.created_at
                else "",
            )
            for assignment in result.all()
        ]

    async def _incident_items(
        self,
        organization_id: str,
        *,
        customer_ids: set[str] | None = None,
        status: str | None = None,
        priority: str | None = None,
        limit: int,
    ) -> list[dict]:
        conditions = [InsuranceIncidentReport.organization_id == organization_id]
        if customer_ids is not None:
            conditions.append(InsuranceIncidentReport.customer_id.in_(customer_ids))
        statement = self._apply_common_filters(
            select(InsuranceIncidentReport).where(*conditions),
            InsuranceIncidentReport,
            status,
            priority,
            limit,
        )
        result = await self.session.scalars(statement)
        return [
            self._queue_item(
                item_type="incident",
                source_id=incident.id,
                organization_id=incident.organization_id,
                customer_id=incident.customer_id,
                employee_user_id=None,
                status=incident.status,
                priority=incident.priority,
                due_at=incident.due_at,
                created_at=incident.created_at.isoformat()
                if incident.created_at
                else "",
            )
            for incident in result.all()
        ]

    async def _appointment_items(
        self,
        organization_id: str,
        *,
        employee_user_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        limit: int,
    ) -> list[dict]:
        conditions = [InsuranceAppointment.organization_id == organization_id]
        if employee_user_id is not None:
            conditions.append(InsuranceAppointment.employee_user_id == employee_user_id)
        statement = self._apply_common_filters(
            select(InsuranceAppointment).where(*conditions),
            InsuranceAppointment,
            status,
            priority,
            limit,
        )
        result = await self.session.scalars(statement)
        return [
            self._queue_item(
                item_type="appointment",
                source_id=appointment.id,
                organization_id=appointment.organization_id,
                customer_id=appointment.customer_id,
                employee_user_id=appointment.employee_user_id,
                status=appointment.status,
                priority=appointment.priority,
                due_at=appointment.due_at,
                created_at=appointment.created_at.isoformat()
                if appointment.created_at
                else "",
            )
            for appointment in result.all()
        ]

    async def _conversation_items(
        self,
        organization_id: str,
        *,
        employee_user_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        limit: int,
    ) -> list[dict]:
        conditions = [InsuranceConversation.organization_id == organization_id]
        if employee_user_id is not None:
            conditions.append(InsuranceConversation.employee_user_id == employee_user_id)
        statement = self._apply_common_filters(
            select(InsuranceConversation).where(*conditions),
            InsuranceConversation,
            status,
            priority,
            limit,
        )
        result = await self.session.scalars(statement)
        return [
            self._queue_item(
                item_type="conversation",
                source_id=conversation.id,
                organization_id=conversation.organization_id,
                customer_id=conversation.customer_id,
                employee_user_id=conversation.employee_user_id,
                status=conversation.status,
                priority=conversation.priority,
                due_at=conversation.due_at,
                created_at=conversation.created_at.isoformat()
                if conversation.created_at
                else "",
            )
            for conversation in result.all()
        ]

    def _apply_common_filters(
        self,
        statement,
        model,
        status: str | None,
        priority: str | None,
        limit: int,
    ):
        conditions = []
        if status:
            conditions.append(model.status == status)
        if priority:
            conditions.append(model.priority == priority)
        if conditions:
            statement = statement.where(and_(*conditions))
        return statement.order_by(model.due_at.asc(), model.created_at.desc()).limit(limit)

    def _queue_item(
        self,
        *,
        item_type: str,
        source_id: str,
        organization_id: str,
        customer_id: str,
        employee_user_id: str | None,
        status: str,
        priority: str,
        due_at: str | None,
        created_at: str,
    ) -> dict:
        return {
            "id": f"{item_type}:{source_id}",
            "item_type": item_type,
            "source_id": source_id,
            "organization_id": organization_id,
            "customer_id": customer_id,
            "employee_user_id": employee_user_id,
            "status": status,
            "priority": priority,
            "due_at": due_at,
            "created_at": created_at,
        }

    def _sort_items(self, items: list[dict]) -> list[dict]:
        return sorted(
            items,
            key=lambda item: (
                item["due_at"] is None,
                item["due_at"] or "",
                item["priority"],
                item["created_at"],
            ),
        )


class WorkloadQueueService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = WorkloadQueueRepository(session)
        self.audit_log = AuditLogService(session)

    async def list_my_queue(
        self,
        *,
        organization_id: str,
        employee_user_id: str,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        return await self.repository.list_for_employee(
            organization_id=organization_id,
            employee_user_id=employee_user_id,
            status=status,
            priority=priority,
            limit=self._bounded_limit(limit),
        )

    async def list_admin_queue(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        return await self.repository.list_for_admin(
            organization_id=organization_id,
            status=status,
            priority=priority,
            limit=self._bounded_limit(limit),
        )

    def _bounded_limit(self, limit: int) -> int:
        return min(max(limit, 1), 100)

    async def get_item(
        self,
        *,
        organization_id: str,
        item_id: str,
        actor_user_id: str,
        role: str,
    ) -> dict:
        item_type, source_id = self._parse_item_id(item_id)
        record = await self._get_source_record(organization_id, item_type, source_id)
        item = self._serialize_source_record(item_type, record)
        await self._ensure_item_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            item=item,
        )
        return item

    async def update_item(
        self,
        *,
        organization_id: str,
        item_id: str,
        actor_user_id: str,
        role: str,
        payload: UpdateQueueItemIn,
    ) -> dict:
        item_type, source_id = self._parse_item_id(item_id)
        record = await self._get_source_record(organization_id, item_type, source_id)
        before = self._serialize_source_record(item_type, record)
        await self._ensure_item_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            item=before,
        )
        if payload.employee_user_id is not None and role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "permission_denied",
                    "message": "Only admins can reassign queue items.",
                },
            )
        if payload.status is not None:
            record.status = payload.status
        if payload.priority is not None:
            record.priority = payload.priority
        if payload.employee_user_id is not None and hasattr(record, "employee_user_id"):
            record.employee_user_id = payload.employee_user_id
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.queue_item_updated",
                resource_type=f"insurance_{item_type}",
                resource_id=source_id,
                metadata={
                    "item_id": item_id,
                    "previous_status": before["status"],
                    "new_status": getattr(record, "status", None),
                    "previous_priority": before["priority"],
                    "new_priority": getattr(record, "priority", None),
                },
            )
        )
        await self.session.commit()
        return self._serialize_source_record(item_type, record)

    def _parse_item_id(self, item_id: str) -> tuple[str, str]:
        if ":" not in item_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_queue_item_id",
                    "message": "Queue item id must use '<type>:<source_id>'.",
                },
            )
        item_type, source_id = item_id.split(":", 1)
        if item_type not in {"assignment", "incident", "appointment", "conversation"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_queue_item_type",
                    "message": "Queue item type is not supported.",
                },
            )
        return item_type, source_id

    async def _get_source_record(
        self, organization_id: str, item_type: str, source_id: str
    ):
        model_by_type = {
            "assignment": InsuranceEmployeeAssignment,
            "incident": InsuranceIncidentReport,
            "appointment": InsuranceAppointment,
            "conversation": InsuranceConversation,
        }
        model = model_by_type[item_type]
        record = await self.session.scalar(
            select(model).where(
                model.organization_id == organization_id,
                model.id == source_id,
            )
        )
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "queue_item_not_found",
                    "message": "Queue item was not found.",
                },
            )
        return record

    def _serialize_source_record(self, item_type: str, record) -> dict:
        return self.repository._queue_item(
            item_type=item_type,
            source_id=record.id,
            organization_id=record.organization_id,
            customer_id=record.customer_id,
            employee_user_id=getattr(record, "employee_user_id", None),
            status=record.status,
            priority=record.priority,
            due_at=record.due_at,
            created_at=record.created_at.isoformat() if record.created_at else "",
        )

    async def _ensure_item_access(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        item: dict,
    ) -> None:
        if role == "admin":
            return
        if role != "employee":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "permission_denied",
                    "message": "You do not have access to this queue item.",
                },
            )
        if item["employee_user_id"] == actor_user_id:
            return
        assigned_customer_ids = await self.repository._assigned_customer_ids(
            organization_id, actor_user_id
        )
        if item["customer_id"] in assigned_customer_ids:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "queue_item_forbidden",
                "message": "Queue item is outside the employee scope.",
            },
        )
