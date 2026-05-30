from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.domains.insurance.correction_service import ClaimCorrectionService
from app.domains.insurance.schemas import SaveClaimCorrectionIn


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class FakeClaims:
    def __init__(self, claim) -> None:
        self.claim = claim

    async def _get_claim(self, organization_id: str, claim_id: str):
        assert organization_id == self.claim.organization_id
        assert claim_id == self.claim.id
        return self.claim

    async def _ensure_read_access(self, **_kwargs) -> None:
        pass


class FakeCorrections:
    def __init__(self) -> None:
        self.records = []

    async def add(self, correction):
        self.records.append(correction)
        return correction

    async def get_for_org(self, organization_id: str, correction_id: str):
        return next(
            (
                record
                for record in self.records
                if record.organization_id == organization_id and record.id == correction_id
            ),
            None,
        )

    async def list_for_claim(self, organization_id: str, claim_id: str, *, limit: int):
        return [
            record
            for record in reversed(self.records)
            if record.organization_id == organization_id and record.claim_id == claim_id
        ][:limit]


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


def build_service() -> tuple[ClaimCorrectionService, SimpleNamespace]:
    claim = SimpleNamespace(id="incident_1", organization_id="org_demo", claim_state="in_review")
    service = ClaimCorrectionService.__new__(ClaimCorrectionService)
    service.session = FakeSession()
    service.claims = FakeClaims(claim)
    service.corrections = FakeCorrections()
    service.audit_log = FakeAuditLog()
    service.idempotency = FakeIdempotency()
    return service, claim


@pytest.mark.asyncio
async def test_reviewer_saves_and_approves_correction_without_mutating_claim_state() -> None:
    service, claim = build_service()

    draft = await service.save_draft(
        organization_id="org_demo",
        claim_id="incident_1",
        actor_user_id="user_employee",
        role="employee",
        idempotency_key="correction-1",
        payload=SaveClaimCorrectionIn(
            corrected_fields={"priority": "high", "incident_type": "medical"}
        ),
    )
    approved = await service.approve(
        organization_id="org_demo",
        claim_id="incident_1",
        correction_id=draft["id"],
        actor_user_id="user_employee",
        role="employee",
        idempotency_key="correction-approve-1",
    )

    assert approved["status"] == "approved"
    assert claim.claim_state == "in_review"
    assert service.audit_log.events[0].metadata == {
        "claim_id": "incident_1",
        "changed_fields": ["incident_type", "priority"],
    }


@pytest.mark.asyncio
async def test_customer_cannot_access_reviewer_corrections() -> None:
    service, _claim = build_service()

    with pytest.raises(HTTPException) as exc:
        await service.list_history(
            organization_id="org_demo",
            claim_id="incident_1",
            actor_user_id="user_customer",
            role="customer",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_correction_rejects_unsupported_sensitive_field() -> None:
    service, _claim = build_service()

    with pytest.raises(HTTPException) as exc:
        await service.save_draft(
            organization_id="org_demo",
            claim_id="incident_1",
            actor_user_id="user_employee",
            role="employee",
            idempotency_key="correction-invalid",
            payload=SaveClaimCorrectionIn(corrected_fields={"description": "raw narrative"}),
        )

    assert exc.value.status_code == 422
