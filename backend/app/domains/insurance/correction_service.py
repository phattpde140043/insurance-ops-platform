from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.insurance.claim_lifecycle_service import ClaimLifecycleService
from app.domains.insurance.models import InsuranceClaimCorrection
from app.domains.insurance.repositories import InsuranceClaimCorrectionRepository
from app.domains.insurance.schemas import SaveClaimCorrectionIn
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService
from app.domains.shared.idempotency_service import IdempotencyService

ALLOWED_CORRECTION_FIELDS = {"incident_type", "policy_id", "priority"}


class ClaimCorrectionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.claims = ClaimLifecycleService(session)
        self.corrections = InsuranceClaimCorrectionRepository(session)
        self.audit_log = AuditLogService(session)
        self.idempotency = IdempotencyService(session)

    async def save_draft(
        self,
        *,
        organization_id: str,
        claim_id: str,
        actor_user_id: str,
        role: str,
        idempotency_key: str,
        payload: SaveClaimCorrectionIn,
    ) -> dict:
        await self._ensure_reviewer_access(
            organization_id=organization_id,
            claim_id=claim_id,
            actor_user_id=actor_user_id,
            role=role,
        )
        changed_fields = sorted(payload.corrected_fields)
        if not changed_fields or not set(changed_fields).issubset(ALLOWED_CORRECTION_FIELDS):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "invalid_correction_fields",
                    "message": "Correction fields are empty or unsupported.",
                },
            )
        reservation = await self.idempotency.reserve(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name="insurance.save_claim_correction",
            idempotency_key=idempotency_key,
            fingerprint_payload={
                "claim_id": claim_id,
                "corrected_fields": payload.corrected_fields,
            },
        )
        if reservation.replayed and reservation.record.resource_id:
            existing = await self.corrections.get_for_org(
                organization_id, reservation.record.resource_id
            )
            if existing is not None:
                return self._serialize(existing)
        correction = InsuranceClaimCorrection(
            id=new_id("claim_correction"),
            organization_id=organization_id,
            claim_id=claim_id,
            reviewer_user_id=actor_user_id,
            status="draft",
            corrected_fields=payload.corrected_fields,
            changed_fields=changed_fields,
        )
        await self.corrections.add(correction)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.claim_correction_saved",
                resource_type="insurance_claim_correction",
                resource_id=correction.id,
                metadata={"claim_id": claim_id, "changed_fields": changed_fields},
            )
        )
        self.idempotency.complete(
            reservation,
            resource_type="insurance_claim_correction",
            resource_id=correction.id,
        )
        await self.session.commit()
        return self._serialize(correction)

    async def approve(
        self,
        *,
        organization_id: str,
        claim_id: str,
        correction_id: str,
        actor_user_id: str,
        role: str,
        idempotency_key: str,
    ) -> dict:
        await self._ensure_reviewer_access(
            organization_id=organization_id,
            claim_id=claim_id,
            actor_user_id=actor_user_id,
            role=role,
        )
        reservation = await self.idempotency.reserve(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name="insurance.approve_claim_correction",
            idempotency_key=idempotency_key,
            fingerprint_payload={"claim_id": claim_id, "correction_id": correction_id},
        )
        correction = await self.corrections.get_for_org(organization_id, correction_id)
        if correction is None or correction.claim_id != claim_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "claim_correction_not_found", "message": "Correction was not found."},
            )
        if reservation.replayed:
            return self._serialize(correction)
        if correction.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "claim_correction_not_draft", "message": "Only draft corrections can be approved."},
            )
        correction.status = "approved"
        correction.approved_by_user_id = actor_user_id
        correction.approved_at = datetime.now(UTC)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.claim_correction_approved",
                resource_type="insurance_claim_correction",
                resource_id=correction.id,
                metadata={"claim_id": claim_id, "changed_fields": correction.changed_fields},
            )
        )
        self.idempotency.complete(
            reservation,
            resource_type="insurance_claim_correction",
            resource_id=correction.id,
        )
        await self.session.commit()
        return self._serialize(correction)

    async def list_history(
        self,
        *,
        organization_id: str,
        claim_id: str,
        actor_user_id: str,
        role: str,
        limit: int = 100,
    ) -> list[dict]:
        await self._ensure_reviewer_access(
            organization_id=organization_id,
            claim_id=claim_id,
            actor_user_id=actor_user_id,
            role=role,
        )
        corrections = await self.corrections.list_for_claim(
            organization_id, claim_id, limit=min(max(limit, 1), 101)
        )
        return [self._serialize(correction) for correction in corrections]

    async def _ensure_reviewer_access(
        self,
        *,
        organization_id: str,
        claim_id: str,
        actor_user_id: str,
        role: str,
    ) -> None:
        if role not in {"admin", "employee"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": "claim_correction_forbidden", "message": "Reviewer access is required."})
        claim = await self.claims._get_claim(organization_id, claim_id)
        await self.claims._ensure_read_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            claim=claim,
        )

    def _serialize(self, correction: InsuranceClaimCorrection) -> dict:
        return {
            "id": correction.id,
            "organization_id": correction.organization_id,
            "claim_id": correction.claim_id,
            "reviewer_user_id": correction.reviewer_user_id,
            "status": correction.status,
            "corrected_fields": correction.corrected_fields,
            "changed_fields": correction.changed_fields,
            "approved_by_user_id": correction.approved_by_user_id,
            "approved_at": correction.approved_at.isoformat() if correction.approved_at else None,
            "created_at": correction.created_at.isoformat() if correction.created_at else "",
        }
