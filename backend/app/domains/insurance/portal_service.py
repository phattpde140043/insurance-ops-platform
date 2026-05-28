from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.insurance.models import (
    InsuranceAppointment,
    InsuranceConversation,
    InsuranceCustomer,
    InsuranceEmployeeAssignment,
    InsuranceIncidentReport,
    InsurancePolicy,
)
from app.domains.insurance.repositories import (
    InsuranceAppointmentRepository,
    InsuranceConversationRepository,
    InsuranceCustomerRepository,
    InsuranceEmployeeAssignmentRepository,
    InsuranceIncidentReportRepository,
    InsurancePolicyRepository,
)
from app.domains.insurance.schemas import (
    CreatePortalAppointmentIn,
    CreatePortalConversationIn,
)
from app.core.model_mixins import new_id
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService


class CustomerPortalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = InsuranceCustomerRepository(session)
        self.assignments = InsuranceEmployeeAssignmentRepository(session)
        self.policies = InsurancePolicyRepository(session)
        self.incidents = InsuranceIncidentReportRepository(session)
        self.appointments = InsuranceAppointmentRepository(session)
        self.conversations = InsuranceConversationRepository(session)
        self.audit_log = AuditLogService(session)

    async def get_summary(self, *, organization_id: str, user_id: str) -> dict:
        customer = await self._get_linked_customer(
            organization_id, user_id
        )

        policies = await self.policies.list_for_customer(
            organization_id, customer.id, limit=10
        )
        incidents = await self.incidents.list_for_customer(
            organization_id, customer.id, limit=10
        )
        appointments = await self.appointments.list_for_customer(
            organization_id, customer.id, limit=10
        )
        conversations = await self.conversations.list_for_customer(
            organization_id, customer.id, limit=10
        )
        return {
            "customer": self._serialize_customer(customer),
            "policies": [self._serialize_policy(policy) for policy in policies],
            "recent_incidents": [
                self._serialize_incident(incident) for incident in incidents
            ],
            "upcoming_appointments": [
                self._serialize_appointment(appointment)
                for appointment in appointments
            ],
            "open_conversations": [
                self._serialize_conversation(conversation)
                for conversation in conversations
                if conversation.status == "open"
            ],
        }

    async def list_policies(
        self, *, organization_id: str, user_id: str, limit: int = 25
    ) -> list[dict]:
        customer = await self._get_linked_customer(organization_id, user_id)
        policies = await self.policies.list_for_customer(
            organization_id, customer.id, limit=self._bounded_limit(limit)
        )
        return [self._serialize_policy(policy) for policy in policies]

    async def list_incidents(
        self, *, organization_id: str, user_id: str, limit: int = 25
    ) -> list[dict]:
        customer = await self._get_linked_customer(organization_id, user_id)
        incidents = await self.incidents.list_for_customer(
            organization_id, customer.id, limit=self._bounded_limit(limit)
        )
        return [self._serialize_incident(incident) for incident in incidents]

    async def list_appointments(
        self, *, organization_id: str, user_id: str, limit: int = 25
    ) -> list[dict]:
        customer = await self._get_linked_customer(organization_id, user_id)
        appointments = await self.appointments.list_for_customer(
            organization_id, customer.id, limit=self._bounded_limit(limit)
        )
        return [
            self._serialize_appointment(appointment)
            for appointment in appointments
        ]

    async def list_conversations(
        self, *, organization_id: str, user_id: str, limit: int = 25
    ) -> list[dict]:
        customer = await self._get_linked_customer(organization_id, user_id)
        conversations = await self.conversations.list_for_customer(
            organization_id, customer.id, limit=self._bounded_limit(limit)
        )
        return [
            self._serialize_conversation(conversation)
            for conversation in conversations
        ]

    async def request_appointment(
        self,
        *,
        organization_id: str,
        user_id: str,
        payload: CreatePortalAppointmentIn,
    ) -> dict:
        customer = await self._get_linked_customer(organization_id, user_id)
        assignment = await self._get_active_assignment(organization_id, customer.id)
        appointment = InsuranceAppointment(
            id=new_id("appointment"),
            organization_id=organization_id,
            customer_id=customer.id,
            employee_user_id=assignment.employee_user_id,
            scheduled_at=payload.scheduled_at,
            status="requested",
        )
        await self.appointments.add(appointment)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=user_id,
                action="insurance.portal_appointment_requested",
                resource_type="insurance_appointment",
                resource_id=appointment.id,
                metadata={"customer_id": customer.id},
            )
        )
        await self.session.commit()
        return self._serialize_appointment(appointment)

    async def start_conversation(
        self,
        *,
        organization_id: str,
        user_id: str,
        payload: CreatePortalConversationIn,
    ) -> dict:
        customer = await self._get_linked_customer(organization_id, user_id)
        assignment = await self.assignments.get_active_for_customer(
            organization_id, customer.id
        )
        conversation = InsuranceConversation(
            id=new_id("conversation"),
            organization_id=organization_id,
            customer_id=customer.id,
            employee_user_id=assignment.employee_user_id if assignment else None,
            status="open",
        )
        await self.conversations.add(conversation)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=user_id,
                action="insurance.portal_conversation_started",
                resource_type="insurance_conversation",
                resource_id=conversation.id,
                metadata={"customer_id": customer.id},
            )
        )
        await self.session.commit()
        return self._serialize_conversation(conversation)

    async def _get_linked_customer(
        self, organization_id: str, user_id: str
    ) -> InsuranceCustomer:
        customer = await self.customers.get_by_linked_user_id(
            organization_id, user_id
        )
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "customer_link_not_found",
                    "message": "No customer profile is linked to this user.",
                },
            )
        return customer

    def _bounded_limit(self, limit: int) -> int:
        return min(max(limit, 1), 100)

    async def _get_active_assignment(
        self, organization_id: str, customer_id: str
    ) -> InsuranceEmployeeAssignment:
        assignment = await self.assignments.get_active_for_customer(
            organization_id, customer_id
        )
        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "employee_assignment_not_found",
                    "message": "No active employee assignment is available.",
                },
            )
        return assignment

    def _serialize_customer(self, customer: InsuranceCustomer) -> dict:
        return {
            "id": customer.id,
            "organization_id": customer.organization_id,
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "assigned_employee_id": None,
            "created_at": customer.created_at.isoformat()
            if customer.created_at
            else "",
        }

    def _serialize_policy(self, policy: InsurancePolicy) -> dict:
        return {
            "id": policy.id,
            "organization_id": policy.organization_id,
            "customer_id": policy.customer_id,
            "plan_id": policy.plan_id,
            "status": policy.status,
            "start_date": policy.start_date.isoformat(),
            "created_at": policy.created_at.isoformat()
            if policy.created_at
            else "",
        }

    def _serialize_incident(self, incident: InsuranceIncidentReport) -> dict:
        return {
            "id": incident.id,
            "organization_id": incident.organization_id,
            "customer_id": incident.customer_id,
            "incident_type": incident.incident_type,
            "description": incident.description,
            "status": incident.status,
            "created_at": incident.created_at.isoformat()
            if incident.created_at
            else "",
        }

    def _serialize_appointment(self, appointment: InsuranceAppointment) -> dict:
        return {
            "id": appointment.id,
            "organization_id": appointment.organization_id,
            "customer_id": appointment.customer_id,
            "employee_user_id": appointment.employee_user_id,
            "scheduled_at": appointment.scheduled_at,
            "status": appointment.status,
            "created_at": appointment.created_at.isoformat()
            if appointment.created_at
            else "",
        }

    def _serialize_conversation(self, conversation: InsuranceConversation) -> dict:
        return {
            "id": conversation.id,
            "organization_id": conversation.organization_id,
            "customer_id": conversation.customer_id,
            "employee_user_id": conversation.employee_user_id,
            "status": conversation.status,
            "created_at": conversation.created_at.isoformat()
            if conversation.created_at
            else "",
        }
