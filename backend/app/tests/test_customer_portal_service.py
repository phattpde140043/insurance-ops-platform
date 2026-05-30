from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.domains.insurance.portal_service import CustomerPortalService
from app.domains.insurance.schemas import (
    CreatePortalAppointmentIn,
    CreatePortalConversationIn,
)
from app.tests.support.tenant_isolation import assert_only_tenant_records


class FakeCustomerRepository:
    def __init__(self, customer=None) -> None:
        self.customer = customer

    async def get_by_linked_user_id(self, organization_id: str, user_id: str):
        if (
            self.customer is not None
            and self.customer.organization_id == organization_id
            and self.customer.linked_user_id == user_id
        ):
            return self.customer
        return None


class FakeScopedRepository:
    def __init__(self, records) -> None:
        self.records = records

    async def list_for_customer(
        self, organization_id: str, customer_id: str, *, limit: int = 10
    ):
        return [
            record
            for record in self.records
            if record.organization_id == organization_id
            and record.customer_id == customer_id
        ][:limit]

    async def add(self, record):
        self.records.append(record)
        return record


class FakeAssignmentRepository:
    async def get_active_for_customer(self, organization_id: str, customer_id: str):
        if organization_id == "org_alpha" and customer_id == "customer_alpha":
            return SimpleNamespace(employee_user_id="user_employee")
        return None


class FakeAuditLog:
    def __init__(self) -> None:
        self.events = []

    async def record(self, event):
        self.events.append(event)
        return event


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeIdempotency:
    async def reserve(self, **_kwargs):
        return SimpleNamespace(replayed=False, record=SimpleNamespace())

    def complete(self, *_args, **_kwargs) -> None:
        pass


def build_portal_service(customer, *, conversations=None) -> CustomerPortalService:
    service = CustomerPortalService.__new__(CustomerPortalService)
    service.session = FakeSession()
    service.customers = FakeCustomerRepository(customer)
    service.assignments = FakeAssignmentRepository()
    service.policies = FakeScopedRepository(
        [
            SimpleNamespace(
                id="policy_alpha",
                organization_id="org_alpha",
                customer_id="customer_alpha",
                plan_id="plan_gold",
                status="active",
                start_date=date(2026, 1, 1),
                created_at=None,
            ),
            SimpleNamespace(
                id="policy_beta",
                organization_id="org_beta",
                customer_id="customer_beta",
                plan_id="plan_silver",
                status="active",
                start_date=date(2026, 1, 1),
                created_at=None,
            ),
        ]
    )
    service.incidents = FakeScopedRepository(
        [
            SimpleNamespace(
                id="incident_alpha",
                organization_id="org_alpha",
                customer_id="customer_alpha",
                incident_type="medical",
                description="Need support",
                status="reported",
                created_at=None,
            )
        ]
    )
    service.appointments = FakeScopedRepository(
        [
            SimpleNamespace(
                id="appointment_alpha",
                organization_id="org_alpha",
                customer_id="customer_alpha",
                employee_user_id="user_employee",
                scheduled_at="2026-06-01T10:00:00Z",
                status="scheduled",
                created_at=None,
            )
        ]
    )
    service.conversations = FakeScopedRepository(
        conversations
        if conversations is not None
        else [
            SimpleNamespace(
                id="conversation_alpha",
                organization_id="org_alpha",
                customer_id="customer_alpha",
                employee_user_id=None,
                status="open",
                created_at=None,
            ),
            SimpleNamespace(
                id="conversation_closed",
                organization_id="org_alpha",
                customer_id="customer_alpha",
                employee_user_id=None,
                status="closed",
                created_at=None,
            ),
        ]
    )
    service.audit_log = FakeAuditLog()
    service.idempotency = FakeIdempotency()
    return service


@pytest.mark.asyncio
async def test_portal_summary_resolves_customer_from_user_scope() -> None:
    customer = SimpleNamespace(
        id="customer_alpha",
        organization_id="org_alpha",
        linked_user_id="user_customer",
        name="Lan Nguyen",
        email="lan@example.com",
        phone=None,
        created_at=None,
    )
    service = build_portal_service(customer)

    result = await service.get_summary(
        organization_id="org_alpha",
        user_id="user_customer",
    )

    assert result["customer"]["id"] == "customer_alpha"
    assert [policy["id"] for policy in result["policies"]] == ["policy_alpha"]
    assert [incident["id"] for incident in result["recent_incidents"]] == [
        "incident_alpha"
    ]
    assert [conversation["id"] for conversation in result["open_conversations"]] == [
        "conversation_alpha"
    ]
    assert_only_tenant_records(result["policies"], "org_alpha")
    assert_only_tenant_records(result["recent_incidents"], "org_alpha")


@pytest.mark.asyncio
async def test_portal_summary_rejects_unlinked_customer() -> None:
    service = build_portal_service(customer=None)

    with pytest.raises(HTTPException) as exc:
        await service.get_summary(
            organization_id="org_alpha",
            user_id="user_customer",
        )

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "customer_link_not_found"


@pytest.mark.asyncio
async def test_portal_history_methods_are_customer_scoped() -> None:
    customer = SimpleNamespace(
        id="customer_alpha",
        organization_id="org_alpha",
        linked_user_id="user_customer",
        name="Lan Nguyen",
        email="lan@example.com",
        phone=None,
        created_at=None,
    )
    service = build_portal_service(customer)

    policies = await service.list_policies(
        organization_id="org_alpha",
        user_id="user_customer",
        limit=25,
    )
    incidents = await service.list_incidents(
        organization_id="org_alpha",
        user_id="user_customer",
        limit=25,
    )
    appointments = await service.list_appointments(
        organization_id="org_alpha",
        user_id="user_customer",
        limit=25,
    )
    conversations = await service.list_conversations(
        organization_id="org_alpha",
        user_id="user_customer",
        limit=25,
    )

    assert [policy["id"] for policy in policies] == ["policy_alpha"]
    assert [incident["id"] for incident in incidents] == ["incident_alpha"]
    assert [appointment["id"] for appointment in appointments] == [
        "appointment_alpha"
    ]
    assert {conversation["id"] for conversation in conversations} == {
        "conversation_alpha",
        "conversation_closed",
    }
    assert_only_tenant_records(policies, "org_alpha")
    assert_only_tenant_records(incidents, "org_alpha")
    assert_only_tenant_records(appointments, "org_alpha")
    assert_only_tenant_records(conversations, "org_alpha")


@pytest.mark.asyncio
async def test_portal_appointment_request_resolves_customer_and_employee() -> None:
    customer = SimpleNamespace(
        id="customer_alpha",
        organization_id="org_alpha",
        linked_user_id="user_customer",
        name="Lan Nguyen",
        email="lan@example.com",
        phone=None,
        created_at=None,
    )
    service = build_portal_service(customer)

    result = await service.request_appointment(
        organization_id="org_alpha",
        user_id="user_customer",
        idempotency_key="appointment-1",
        payload=CreatePortalAppointmentIn(scheduled_at="2026-06-01T10:00:00Z"),
    )

    assert result["customer_id"] == "customer_alpha"
    assert result["employee_user_id"] == "user_employee"
    assert result["status"] == "requested"
    assert service.session.committed
    assert service.audit_log.events[0].action == (
        "insurance.portal_appointment_requested"
    )


@pytest.mark.asyncio
async def test_portal_conversation_start_resolves_customer_scope() -> None:
    customer = SimpleNamespace(
        id="customer_alpha",
        organization_id="org_alpha",
        linked_user_id="user_customer",
        name="Lan Nguyen",
        email="lan@example.com",
        phone=None,
        created_at=None,
    )
    service = build_portal_service(customer)

    result = await service.start_conversation(
        organization_id="org_alpha",
        user_id="user_customer",
        idempotency_key="conversation-1",
        payload=CreatePortalConversationIn(),
    )

    assert result["customer_id"] == "customer_alpha"
    assert result["employee_user_id"] == "user_employee"
    assert result["status"] == "open"
    assert service.session.committed
    assert service.audit_log.events[0].action == (
        "insurance.portal_conversation_started"
    )
