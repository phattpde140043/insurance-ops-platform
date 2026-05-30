from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.insurance.models import InsuranceClaimTransition, InsuranceIncidentReport
from app.domains.insurance.repositories import (
    InsuranceClaimTransitionRepository,
    InsuranceCustomerRepository,
    InsuranceEmployeeAssignmentRepository,
    InsuranceIncidentReportRepository,
)
from app.domains.insurance.schemas import CreateClaimTransitionIn
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService
from app.domains.shared.outbox_service import DomainOutboxService
from app.domains.shared.idempotency_service import IdempotencyService


ALLOWED_TRANSITIONS = {
    ("reported", "triage", "employee"),
    ("reported", "triage", "admin"),
    ("triage", "in_review", "employee"),
    ("triage", "in_review", "admin"),
    ("in_review", "approved", "employee"),
    ("in_review", "approved", "admin"),
    ("in_review", "rejected", "employee"),
    ("in_review", "rejected", "admin"),
    ("approved", "closed", "employee"),
    ("approved", "closed", "admin"),
    ("rejected", "reopened", "admin"),
    ("closed", "reopened", "admin"),
    ("reopened", "triage", "employee"),
    ("reopened", "triage", "admin"),
}

VALID_STATES = {
    "reported",
    "triage",
    "in_review",
    "approved",
    "rejected",
    "closed",
    "reopened",
}


class ClaimLifecycleService:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        if session is not None:
            self.claims = InsuranceIncidentReportRepository(session)
            self.transitions = InsuranceClaimTransitionRepository(session)
            self.customers = InsuranceCustomerRepository(session)
            self.assignments = InsuranceEmployeeAssignmentRepository(session)
        self.audit_log = AuditLogService(session)
        self.outbox = DomainOutboxService(session)
        self.idempotency = IdempotencyService(session)

    def can_transition(self, from_state: str, to_state: str, role: str) -> bool:
        return (from_state, to_state, role) in ALLOWED_TRANSITIONS

    def allowed_transitions(self, from_state: str, role: str) -> list[str]:
        return sorted(
            to_state
            for current_state, to_state, allowed_role in ALLOWED_TRANSITIONS
            if current_state == from_state and allowed_role == role
        )

    async def get_claim_detail(
        self,
        *,
        organization_id: str,
        claim_id: str,
        actor_user_id: str,
        role: str,
    ) -> dict:
        claim = await self._get_claim(organization_id, claim_id)
        await self._ensure_read_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            claim=claim,
        )
        return self._serialize_claim(claim, role=role)

    async def list_claim_history(
        self,
        *,
        organization_id: str,
        claim_id: str,
        actor_user_id: str,
        role: str,
        limit: int = 100,
    ) -> list[dict]:
        claim = await self._get_claim(organization_id, claim_id)
        await self._ensure_read_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            claim=claim,
        )
        history = await self.transitions.list_for_claim(
            organization_id, claim_id, limit=min(max(limit, 1), 101)
        )
        return [self._serialize_transition(transition) for transition in history]

    async def transition_claim(
        self,
        *,
        organization_id: str,
        claim_id: str,
        actor_user_id: str,
        role: str,
        idempotency_key: str,
        payload: CreateClaimTransitionIn,
    ) -> dict:
        claim = await self._get_claim(organization_id, claim_id)
        await self._ensure_read_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            claim=claim,
        )
        reservation = await self.idempotency.reserve(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name="insurance.transition_claim",
            idempotency_key=idempotency_key,
            fingerprint_payload={
                "claim_id": claim_id,
                "to_state": payload.to_state,
                "reason": payload.reason,
            },
        )
        if reservation.replayed:
            return self._serialize_claim(claim, role=role)
        reason = payload.reason.strip()
        if not reason:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "claim_transition_reason_required",
                    "message": "Claim transition reason is required.",
                },
            )
        if payload.to_state not in VALID_STATES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "invalid_claim_state",
                    "message": "Target claim state is not supported.",
                },
            )
        if not self.can_transition(claim.claim_state, payload.to_state, role):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "invalid_claim_transition",
                    "message": "Claim cannot transition to the requested state.",
                },
            )
        previous_state = claim.claim_state
        claim.claim_state = payload.to_state
        claim.status = payload.to_state
        transition = InsuranceClaimTransition(
            id=new_id("claim_transition"),
            organization_id=organization_id,
            claim_id=claim.id,
            actor_user_id=actor_user_id,
            from_state=previous_state,
            to_state=payload.to_state,
            reason=reason,
        )
        await self.transitions.add(transition)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.claim_transitioned",
                resource_type="insurance_claim",
                resource_id=claim.id,
                metadata={
                    "from_state": previous_state,
                    "to_state": payload.to_state,
                },
            )
        )
        outbox = getattr(self, "outbox", None)
        if outbox is not None:
            await outbox.append(
                organization_id=organization_id,
                event_type="ClaimTransitioned",
                aggregate_type="insurance_claim",
                aggregate_id=claim.id,
                producer_module="insurance",
                payload={
                    "from_state": previous_state,
                    "to_state": payload.to_state,
                },
                idempotency_key=idempotency_key,
            )
        self.idempotency.complete(
            reservation,
            resource_type="insurance_claim_transition",
            resource_id=transition.id,
            response_metadata={"claim_id": claim.id, "to_state": payload.to_state},
        )
        if self.session is not None:
            await self.session.commit()
        return self._serialize_claim(claim, role=role)

    async def _get_claim(
        self, organization_id: str, claim_id: str
    ) -> InsuranceIncidentReport:
        claim = await self.claims.get_for_org(organization_id, claim_id)
        if claim is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "claim_not_found",
                    "message": "Claim was not found.",
                },
            )
        return claim

    async def _ensure_read_access(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        claim: InsuranceIncidentReport,
    ) -> None:
        if role == "admin":
            return
        if role == "employee":
            customer_ids = await self.assignments.list_customer_ids_for_employee(
                organization_id, actor_user_id
            )
            if claim.customer_id in customer_ids:
                return
        if role == "customer":
            customer = await self.customers.get_by_linked_user_id(
                organization_id, actor_user_id
            )
            if customer is not None and customer.id == claim.customer_id:
                return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "claim_forbidden",
                "message": "Claim is outside the actor scope.",
            },
        )

    def _serialize_claim(self, claim: InsuranceIncidentReport, *, role: str) -> dict:
        return {
            "id": claim.id,
            "organization_id": claim.organization_id,
            "customer_id": claim.customer_id,
            "incident_type": claim.incident_type,
            "description": claim.description,
            "status": claim.status,
            "claim_state": claim.claim_state,
            "created_at": claim.created_at.isoformat() if claim.created_at else "",
            "allowed_transitions": self.allowed_transitions(claim.claim_state, role),
        }

    def _serialize_transition(self, transition: InsuranceClaimTransition) -> dict:
        return {
            "id": transition.id,
            "organization_id": transition.organization_id,
            "claim_id": transition.claim_id,
            "actor_user_id": transition.actor_user_id,
            "from_state": transition.from_state,
            "to_state": transition.to_state,
            "reason": transition.reason,
            "created_at": transition.created_at.isoformat()
            if transition.created_at
            else "",
        }
