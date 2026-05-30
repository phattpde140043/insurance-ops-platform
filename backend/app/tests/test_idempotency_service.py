from contextlib import asynccontextmanager

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.domains.shared.idempotency_service import IdempotencyService
from app.domains.shared.models import IdempotencyRecord


class FakeSession:
    @asynccontextmanager
    async def begin_nested(self):
        yield


class FakeRepository:
    def __init__(self, existing: IdempotencyRecord | None = None) -> None:
        self.existing = existing
        self.added: list[IdempotencyRecord] = []
        self.raise_on_add = False

    async def get_for_command(self, **_kwargs):
        return self.existing

    async def add(self, record: IdempotencyRecord):
        if self.raise_on_add:
            raise IntegrityError("insert", {}, Exception("duplicate"))
        self.added.append(record)
        return record


def build_record(*, fingerprint: str, status: str = "completed") -> IdempotencyRecord:
    return IdempotencyRecord(
        id="idempotency_1",
        organization_id="org_demo",
        actor_user_id="user_customer",
        command_name="insurance.create_incident",
        idempotency_key="incident-1",
        request_fingerprint=fingerprint,
        status=status,
        resource_type="insurance_claim",
        resource_id="incident_1",
        response_metadata={},
    )


@pytest.mark.asyncio
async def test_completed_matching_request_is_replayed() -> None:
    service = IdempotencyService(FakeSession())  # type: ignore[arg-type]
    fingerprint = service._fingerprint({"customer_id": "customer_1"})
    service.repository = FakeRepository(build_record(fingerprint=fingerprint))  # type: ignore[assignment]

    reservation = await service.reserve(
        organization_id="org_demo",
        actor_user_id="user_customer",
        command_name="insurance.create_incident",
        idempotency_key="incident-1",
        fingerprint_payload={"customer_id": "customer_1"},
    )

    assert reservation.replayed is True
    assert reservation.record.resource_id == "incident_1"


@pytest.mark.asyncio
async def test_conflicting_payload_returns_deterministic_conflict() -> None:
    service = IdempotencyService(FakeSession())  # type: ignore[arg-type]
    service.repository = FakeRepository(build_record(fingerprint="other"))  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        await service.reserve(
            organization_id="org_demo",
            actor_user_id="user_customer",
            command_name="insurance.create_incident",
            idempotency_key="incident-1",
            fingerprint_payload={"customer_id": "customer_2"},
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "idempotency_key_conflict"


@pytest.mark.asyncio
async def test_missing_key_is_rejected() -> None:
    service = IdempotencyService(FakeSession())  # type: ignore[arg-type]
    service.repository = FakeRepository()  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        await service.reserve(
            organization_id="org_demo",
            actor_user_id="user_customer",
            command_name="insurance.create_incident",
            idempotency_key=" ",
            fingerprint_payload={},
        )

    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "idempotency_key_required"


@pytest.mark.asyncio
async def test_concurrent_reservation_returns_in_progress_conflict() -> None:
    service = IdempotencyService(FakeSession())  # type: ignore[arg-type]
    fingerprint = service._fingerprint({"customer_id": "customer_1"})
    repository = FakeRepository()
    repository.raise_on_add = True

    calls = 0

    async def get_after_competing_insert(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return None
        return build_record(fingerprint=fingerprint, status="processing")

    repository.get_for_command = get_after_competing_insert  # type: ignore[method-assign]
    service.repository = repository  # type: ignore[assignment]

    with pytest.raises(HTTPException) as exc:
        await service.reserve(
            organization_id="org_demo",
            actor_user_id="user_customer",
            command_name="insurance.create_incident",
            idempotency_key="incident-1",
            fingerprint_payload={"customer_id": "customer_1"},
        )

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "idempotency_request_in_progress"
