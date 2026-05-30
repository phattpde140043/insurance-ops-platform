from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.shared.models import IdempotencyRecord
from app.domains.shared.repositories import IdempotencyRecordRepository


@dataclass(frozen=True)
class IdempotencyReservation:
    record: IdempotencyRecord
    replayed: bool


class IdempotencyService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = IdempotencyRecordRepository(session)

    async def reserve(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        command_name: str,
        idempotency_key: str,
        fingerprint_payload: dict[str, Any],
    ) -> IdempotencyReservation:
        normalized_key = idempotency_key.strip()
        if not normalized_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "idempotency_key_required",
                    "message": "X-Idempotency-Key is required for this command.",
                },
            )
        fingerprint = self._fingerprint(fingerprint_payload)
        existing = await self.repository.get_for_command(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name=command_name,
            idempotency_key=normalized_key,
        )
        if existing is not None:
            return self._validate_existing(existing, fingerprint)

        record = IdempotencyRecord(
            id=new_id("idempotency"),
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name=command_name,
            idempotency_key=normalized_key,
            request_fingerprint=fingerprint,
            status="processing",
            response_metadata={},
        )
        try:
            async with self.session.begin_nested():
                await self.repository.add(record)
        except IntegrityError:
            existing = await self.repository.get_for_command(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                command_name=command_name,
                idempotency_key=normalized_key,
            )
            if existing is None:
                raise
            return self._validate_existing(existing, fingerprint)
        return IdempotencyReservation(record=record, replayed=False)

    def complete(
        self,
        reservation: IdempotencyReservation,
        *,
        resource_type: str,
        resource_id: str,
        response_metadata: dict[str, Any] | None = None,
    ) -> None:
        reservation.record.status = "completed"
        reservation.record.resource_type = resource_type
        reservation.record.resource_id = resource_id
        reservation.record.response_metadata = response_metadata or {}

    def _validate_existing(
        self, record: IdempotencyRecord, fingerprint: str
    ) -> IdempotencyReservation:
        if record.request_fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "idempotency_key_conflict",
                    "message": "X-Idempotency-Key was already used for another request.",
                },
            )
        if record.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "idempotency_request_in_progress",
                    "message": "A request with this X-Idempotency-Key is still in progress.",
                },
            )
        return IdempotencyReservation(record=record, replayed=True)

    def _fingerprint(self, payload: dict[str, Any]) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return sha256(serialized.encode("utf-8")).hexdigest()
