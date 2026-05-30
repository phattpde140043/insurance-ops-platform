from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.domains.insurance.claim_lifecycle_service import ClaimLifecycleService
from app.domains.insurance.schemas import CreateClaimTransitionIn


class FakeClaimRepository:
    def __init__(self, claim) -> None:
        self.claim = claim

    async def get_for_org(self, organization_id: str, claim_id: str):
        if self.claim.organization_id == organization_id and self.claim.id == claim_id:
            return self.claim
        return None


class FakeTransitionRepository:
    def __init__(self) -> None:
        self.transitions = []

    async def add(self, transition):
        self.transitions.append(transition)
        return transition

    async def list_for_claim(
        self, organization_id: str, claim_id: str, *, limit: int = 100
    ):
        return [
            transition
            for transition in self.transitions
            if transition.organization_id == organization_id
            and transition.claim_id == claim_id
        ][:limit]


class FakeAssignments:
    async def list_customer_ids_for_employee(
        self, _organization_id: str, employee_user_id: str
    ) -> set[str]:
        if employee_user_id == "user_employee":
            return {"customer_lan"}
        return set()


class FakeCustomers:
    async def get_by_linked_user_id(self, _organization_id: str, user_id: str):
        if user_id == "user_customer":
            return SimpleNamespace(id="customer_lan")
        return None


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeAuditLog:
    def __init__(self) -> None:
        self.events = []

    async def record(self, event):
        self.events.append(event)
        return event


class FakeIdempotency:
    async def reserve(self, **_kwargs):
        return SimpleNamespace(replayed=False, record=SimpleNamespace())

    def complete(self, *_args, **_kwargs) -> None:
        pass


def build_service(claim) -> ClaimLifecycleService:
    service = ClaimLifecycleService.__new__(ClaimLifecycleService)
    service.session = FakeSession()
    service.claims = FakeClaimRepository(claim)
    service.transitions = FakeTransitionRepository()
    service.assignments = FakeAssignments()
    service.customers = FakeCustomers()
    service.audit_log = FakeAuditLog()
    service.idempotency = FakeIdempotency()
    return service


def build_claim(state: str = "reported"):
    return SimpleNamespace(
        id="incident_1",
        organization_id="org_demo",
        customer_id="customer_lan",
        incident_type="medical",
        description="Follow-up needed",
        status=state,
        claim_state=state,
        created_at=None,
    )


@pytest.mark.asyncio
async def test_employee_can_transition_assigned_claim_and_records_history() -> None:
    claim = build_claim("reported")
    service = build_service(claim)

    result = await service.transition_claim(
        organization_id="org_demo",
        claim_id="incident_1",
        actor_user_id="user_employee",
        role="employee",
        idempotency_key="transition-1",
        payload=CreateClaimTransitionIn(to_state="triage", reason="Ready for triage"),
    )

    assert result["claim_state"] == "triage"
    assert claim.status == "triage"
    assert service.transitions.transitions[0].from_state == "reported"
    assert service.audit_log.events[0].action == "insurance.claim_transitioned"
    assert service.session.committed


@pytest.mark.asyncio
async def test_customer_can_read_but_cannot_transition_claim() -> None:
    service = build_service(build_claim("reported"))

    detail = await service.get_claim_detail(
        organization_id="org_demo",
        claim_id="incident_1",
        actor_user_id="user_customer",
        role="customer",
    )

    assert detail["claim_state"] == "reported"
    assert detail["allowed_transitions"] == []
    assert not service.can_transition("reported", "triage", "customer")


@pytest.mark.asyncio
async def test_invalid_transition_is_rejected() -> None:
    service = build_service(build_claim("closed"))

    with pytest.raises(HTTPException) as exc:
        await service.transition_claim(
            organization_id="org_demo",
            claim_id="incident_1",
            actor_user_id="user_employee",
            role="employee",
            idempotency_key="transition-invalid",
            payload=CreateClaimTransitionIn(to_state="approved", reason="Skip ahead"),
        )

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_employee_outside_assignment_cannot_read_claim() -> None:
    service = build_service(build_claim("reported"))

    with pytest.raises(HTTPException) as exc:
        await service.get_claim_detail(
            organization_id="org_demo",
            claim_id="incident_1",
            actor_user_id="user_other_employee",
            role="employee",
        )

    assert exc.value.status_code == 403
