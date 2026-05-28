import pytest
from fastapi import HTTPException

from app.domains.insurance.queue_service import (
    WorkloadQueueRepository,
    WorkloadQueueService,
)
from app.domains.insurance.schemas import UpdateQueueItemIn
from types import SimpleNamespace

from app.tests.support.tenant_isolation import assert_only_tenant_records


class FakeQueueRepository:
    async def list_for_employee(
        self,
        *,
        organization_id: str,
        employee_user_id: str,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        items = [
            {
                "id": "assignment:a1",
                "item_type": "assignment",
                "source_id": "a1",
                "organization_id": organization_id,
                "customer_id": "customer_lan",
                "employee_user_id": employee_user_id,
                "status": status or "active",
                "priority": priority or "normal",
                "due_at": None,
                "created_at": "",
            }
        ]
        return items[:limit]

    async def list_for_admin(
        self,
        *,
        organization_id: str,
        status: str | None = None,
        priority: str | None = None,
        limit: int = 25,
    ) -> list[dict]:
        return [
            {
                "id": "incident:i1",
                "item_type": "incident",
                "source_id": "i1",
                "organization_id": organization_id,
                "customer_id": "customer_lan",
                "employee_user_id": None,
                "status": status or "reported",
                "priority": priority or "normal",
                "due_at": None,
                "created_at": "",
            }
        ][:limit]


def build_queue_service() -> WorkloadQueueService:
    service = WorkloadQueueService.__new__(WorkloadQueueService)
    service.repository = FakeQueueRepository()
    return service


class FakeMutableSession:
    def __init__(self, record) -> None:
        self.record = record
        self.committed = False

    async def scalar(self, _statement):
        return self.record

    async def commit(self) -> None:
        self.committed = True


class FakeAuditLog:
    def __init__(self) -> None:
        self.events = []

    async def record(self, event):
        self.events.append(event)
        return event


def build_mutating_queue_service(record) -> WorkloadQueueService:
    service = WorkloadQueueService.__new__(WorkloadQueueService)
    service.session = FakeMutableSession(record)
    service.repository = WorkloadQueueRepository.__new__(WorkloadQueueRepository)

    async def assigned_customer_ids(_organization_id, _employee_user_id):
        return {"customer_lan"}

    service.repository._assigned_customer_ids = assigned_customer_ids
    service.audit_log = FakeAuditLog()
    return service


@pytest.mark.asyncio
async def test_employee_queue_is_bounded_and_tenant_scoped() -> None:
    service = build_queue_service()

    result = await service.list_my_queue(
        organization_id="org_demo",
        employee_user_id="user_employee",
        limit=500,
    )

    assert len(result) == 1
    assert result[0]["employee_user_id"] == "user_employee"
    assert_only_tenant_records(result, "org_demo")


@pytest.mark.asyncio
async def test_admin_queue_applies_filters() -> None:
    service = build_queue_service()

    result = await service.list_admin_queue(
        organization_id="org_demo",
        status="reported",
        priority="high",
        limit=25,
    )

    assert result[0]["status"] == "reported"
    assert result[0]["priority"] == "high"
    assert_only_tenant_records(result, "org_demo")


@pytest.mark.asyncio
async def test_admin_can_update_queue_item_status_and_priority() -> None:
    record = SimpleNamespace(
        id="assignment_lan",
        organization_id="org_demo",
        customer_id="customer_lan",
        employee_user_id="user_employee",
        status="active",
        priority="normal",
        due_at=None,
        created_at=None,
    )
    service = build_mutating_queue_service(record)

    result = await service.update_item(
        organization_id="org_demo",
        item_id="assignment:assignment_lan",
        actor_user_id="user_admin",
        role="admin",
        payload=UpdateQueueItemIn(status="in_progress", priority="high"),
    )

    assert result["status"] == "in_progress"
    assert result["priority"] == "high"
    assert service.session.committed
    assert service.audit_log.events[0].action == "insurance.queue_item_updated"


@pytest.mark.asyncio
async def test_employee_cannot_reassign_queue_item() -> None:
    record = SimpleNamespace(
        id="assignment_lan",
        organization_id="org_demo",
        customer_id="customer_lan",
        employee_user_id="user_employee",
        status="active",
        priority="normal",
        due_at=None,
        created_at=None,
    )
    service = build_mutating_queue_service(record)

    with pytest.raises(HTTPException) as exc:
        await service.update_item(
            organization_id="org_demo",
            item_id="assignment:assignment_lan",
            actor_user_id="user_employee",
            role="employee",
            payload=UpdateQueueItemIn(employee_user_id="user_other"),
        )

    assert exc.value.status_code == 403
