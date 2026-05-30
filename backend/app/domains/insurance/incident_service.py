from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.insurance.models import InsuranceIncidentReport
from app.domains.insurance.repositories import (
    InsuranceCustomerRepository,
    InsuranceIncidentReportRepository,
)
from app.domains.insurance.schemas import CreateIncidentIn
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService
from app.domains.shared.outbox_service import DomainOutboxService
from app.domains.shared.idempotency_service import IdempotencyService


class InsuranceIncidentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = InsuranceCustomerRepository(session)
        self.incidents = InsuranceIncidentReportRepository(session)
        self.audit_log = AuditLogService(session)
        self.outbox = DomainOutboxService(session)
        self.idempotency = IdempotencyService(session)

    async def list_incidents(self, organization_id: str, *, limit: int = 50) -> list[dict]:
        incidents = await self.incidents.list_for_org(organization_id, limit=limit)
        return [self._serialize(incident) for incident in incidents]

    async def create_incident(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        idempotency_key: str,
        payload: CreateIncidentIn,
    ) -> dict:
        reservation = await self.idempotency.reserve(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name="insurance.create_incident",
            idempotency_key=idempotency_key,
            fingerprint_payload=payload.model_dump(),
        )
        if reservation.replayed and reservation.record.resource_id:
            existing = await self.incidents.get_for_org(
                organization_id, reservation.record.resource_id
            )
            if existing is not None:
                return self._serialize(existing)
        customer = await self.customers.get_for_org(organization_id, payload.customer_id)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "customer_not_found",
                    "message": "Insurance customer was not found.",
                },
            )
        if role == "customer":
            linked_customer = await self.customers.get_by_linked_user_id(
                organization_id, actor_user_id
            )
            if linked_customer is None or linked_customer.id != customer.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "incident_customer_forbidden",
                        "message": "Customers can report incidents only for their linked profile.",
                    },
                )
        incident = InsuranceIncidentReport(
            id=new_id("incident"),
            organization_id=organization_id,
            customer_id=payload.customer_id,
            incident_type=payload.incident_type,
            description=payload.description,
            status="reported",
            claim_state="reported",
        )
        await self.incidents.add(incident)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.incident_reported",
                resource_type="insurance_incident",
                resource_id=incident.id,
                metadata={
                    "customer_id": payload.customer_id,
                    "incident_type": payload.incident_type,
                },
            )
        )
        outbox = getattr(self, "outbox", None)
        if outbox is not None:
            await outbox.append(
                organization_id=organization_id,
                event_type="IncidentReported",
                aggregate_type="insurance_claim",
                aggregate_id=incident.id,
                producer_module="insurance",
                payload={"customer_id": payload.customer_id, "claim_state": "reported"},
                idempotency_key=idempotency_key,
            )
        self.idempotency.complete(
            reservation,
            resource_type="insurance_claim",
            resource_id=incident.id,
        )
        await self.session.commit()
        return self._serialize(incident)

    def _serialize(self, incident: InsuranceIncidentReport) -> dict:
        return {
            "id": incident.id,
            "organization_id": incident.organization_id,
            "customer_id": incident.customer_id,
            "incident_type": incident.incident_type,
            "description": incident.description,
            "status": incident.status,
            "claim_state": incident.claim_state,
            "created_at": incident.created_at.isoformat()
            if incident.created_at
            else "",
        }
