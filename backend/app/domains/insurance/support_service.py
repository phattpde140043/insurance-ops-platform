from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.ai.chat_service import GuardedChatbotService
from app.domains.insurance.models import (
    InsuranceAppointment,
    InsuranceConversation,
    InsuranceMessage,
)
from app.domains.insurance.repositories import (
    InsuranceAppointmentRepository,
    InsuranceConversationRepository,
    InsuranceCustomerRepository,
    InsuranceEmployeeAssignmentRepository,
    InsuranceIncidentReportRepository,
    InsuranceMessageRepository,
)
from app.domains.insurance.schemas import (
    CreateAppointmentIn,
    CreateConversationIn,
    CreateMessageIn,
)
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService


class InsuranceSupportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.customers = InsuranceCustomerRepository(session)
        self.assignments = InsuranceEmployeeAssignmentRepository(session)
        self.claims = InsuranceIncidentReportRepository(session)
        self.appointments = InsuranceAppointmentRepository(session)
        self.conversations = InsuranceConversationRepository(session)
        self.messages = InsuranceMessageRepository(session)
        self.chatbot = GuardedChatbotService(session)
        self.audit_log = AuditLogService(session)

    async def create_appointment(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        payload: CreateAppointmentIn,
    ) -> dict:
        await self._ensure_customer(organization_id, payload.customer_id)
        appointment = InsuranceAppointment(
            id=new_id("appointment"),
            organization_id=organization_id,
            customer_id=payload.customer_id,
            employee_user_id=payload.employee_user_id,
            scheduled_at=payload.scheduled_at,
            status="scheduled",
        )
        await self.appointments.add(appointment)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.appointment_created",
                resource_type="insurance_appointment",
                resource_id=appointment.id,
            )
        )
        await self.session.commit()
        return self._serialize_appointment(appointment)

    async def create_conversation(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        payload: CreateConversationIn,
    ) -> dict:
        await self._ensure_customer(organization_id, payload.customer_id)
        if payload.claim_id is not None:
            claim = await self.claims.get_for_org(organization_id, payload.claim_id)
            if claim is None or claim.customer_id != payload.customer_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "code": "claim_not_found",
                        "message": "Claim was not found for this customer.",
                    },
                )
        conversation = InsuranceConversation(
            id=new_id("conversation"),
            organization_id=organization_id,
            customer_id=payload.customer_id,
            claim_id=payload.claim_id,
            employee_user_id=payload.employee_user_id,
            status="open",
        )
        await self.conversations.add(conversation)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.conversation_created",
                resource_type="insurance_conversation",
                resource_id=conversation.id,
            )
        )
        await self.session.commit()
        return self._serialize_conversation(conversation)

    async def open_claim_conversation(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        claim_id: str,
    ) -> dict:
        claim = await self.claims.get_for_org(organization_id, claim_id)
        if claim is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "claim_not_found",
                    "message": "Claim was not found.",
                },
            )
        await self._ensure_claim_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            customer_id=claim.customer_id,
        )
        existing = await self.conversations.get_open_for_claim(organization_id, claim_id)
        if existing is not None:
            return self._serialize_conversation(existing)
        conversation = InsuranceConversation(
            id=new_id("conversation"),
            organization_id=organization_id,
            customer_id=claim.customer_id,
            claim_id=claim.id,
            employee_user_id=actor_user_id if role == "employee" else None,
            status="open",
        )
        await self.conversations.add(conversation)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="insurance.claim_conversation_opened",
                resource_type="insurance_conversation",
                resource_id=conversation.id,
                metadata={"claim_id": claim.id},
            )
        )
        await self.session.commit()
        return self._serialize_conversation(conversation)

    async def create_message(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        conversation_id: str,
        payload: CreateMessageIn,
    ) -> dict:
        conversation = await self.conversations.get_for_org(
            organization_id, conversation_id
        )
        await self._ensure_conversation_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            conversation=conversation,
        )
        message = InsuranceMessage(
            id=new_id("message"),
            organization_id=organization_id,
            conversation_id=conversation_id,
            sender_user_id=actor_user_id,
            role="user",
            body=payload.body,
            citations_json={"chunk_ids": []},
        )
        await self.messages.add(message)
        if payload.use_ai:
            ai_response = await self.chatbot.answer(
                organization_id=organization_id,
                user_id=actor_user_id,
                message=payload.body,
            )
            await self.messages.add(
                InsuranceMessage(
                    id=new_id("message"),
                    organization_id=organization_id,
                    conversation_id=conversation_id,
                    sender_user_id=None,
                    role="assistant",
                    body=ai_response["answer"],
                    citations_json={"chunk_ids": ai_response["citations"]},
                )
            )
        await self.session.commit()
        return self._serialize_message(message)

    async def list_conversations(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        limit: int = 25,
    ) -> list[dict]:
        limit = self._bounded_limit(limit)
        if role == "admin":
            conversations = await self.conversations.list_for_org(
                organization_id, limit=limit
            )
        elif role == "employee":
            customer_ids = await self.assignments.list_customer_ids_for_employee(
                organization_id, actor_user_id
            )
            conversations = await self.conversations.list_visible_for_employee(
                organization_id, actor_user_id, customer_ids, limit=limit
            )
        elif role == "customer":
            customer = await self.customers.get_by_linked_user_id(
                organization_id, actor_user_id
            )
            conversations = (
                await self.conversations.list_for_customer(
                    organization_id, customer.id, limit=limit
                )
                if customer is not None
                else []
            )
        else:
            conversations = []
        return [self._serialize_conversation(conversation) for conversation in conversations]

    async def get_conversation_detail(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        conversation_id: str,
        limit: int = 50,
    ) -> dict:
        conversation = await self.conversations.get_for_org(
            organization_id, conversation_id
        )
        await self._ensure_conversation_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            conversation=conversation,
        )
        messages = await self.messages.list_for_conversation(
            organization_id, conversation_id, limit=self._bounded_limit(limit)
        )
        return {
            **self._serialize_conversation(conversation),
            "messages": [self._serialize_message(message) for message in messages],
        }

    async def list_messages(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        conversation_id: str,
        limit: int = 50,
    ) -> list[dict]:
        conversation = await self.conversations.get_for_org(
            organization_id, conversation_id
        )
        await self._ensure_conversation_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            conversation=conversation,
        )
        messages = await self.messages.list_for_conversation(
            organization_id, conversation_id, limit=self._bounded_limit(limit)
        )
        return [self._serialize_message(message) for message in messages]

    async def _ensure_customer(self, organization_id: str, customer_id: str) -> None:
        customer = await self.customers.get_for_org(organization_id, customer_id)
        if customer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "customer_not_found",
                    "message": "Insurance customer was not found.",
                },
            )

    async def _ensure_conversation_access(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        conversation: InsuranceConversation | None,
    ) -> None:
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "conversation_not_found",
                    "message": "Insurance conversation was not found.",
                },
            )
        if role == "admin":
            return
        if role == "employee":
            if conversation.employee_user_id == actor_user_id:
                return
            customer_ids = await self.assignments.list_customer_ids_for_employee(
                organization_id, actor_user_id
            )
            if conversation.customer_id in customer_ids:
                return
        if role == "customer":
            customer = await self.customers.get_by_linked_user_id(
                organization_id, actor_user_id
            )
            if customer is not None and customer.id == conversation.customer_id:
                return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "conversation_forbidden",
                "message": "Conversation is outside the actor scope.",
            },
        )

    async def _ensure_claim_access(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        role: str,
        customer_id: str,
    ) -> None:
        if role == "admin":
            return
        if role == "employee":
            customer_ids = await self.assignments.list_customer_ids_for_employee(
                organization_id, actor_user_id
            )
            if customer_id in customer_ids:
                return
        if role == "customer":
            customer = await self.customers.get_by_linked_user_id(
                organization_id, actor_user_id
            )
            if customer is not None and customer.id == customer_id:
                return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "claim_forbidden",
                "message": "Claim is outside the actor scope.",
            },
        )

    def _bounded_limit(self, limit: int) -> int:
        return min(max(limit, 1), 100)

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
            "claim_id": getattr(conversation, "claim_id", None),
            "employee_user_id": conversation.employee_user_id,
            "status": conversation.status,
            "created_at": conversation.created_at.isoformat()
            if conversation.created_at
            else "",
        }

    def _serialize_message(self, message: InsuranceMessage) -> dict:
        return {
            "id": message.id,
            "organization_id": message.organization_id,
            "conversation_id": message.conversation_id,
            "sender_user_id": message.sender_user_id,
            "role": getattr(message, "role", "user"),
            "body": message.body,
            "citations": getattr(message, "citations_json", {}).get("chunk_ids", []),
            "created_at": message.created_at.isoformat() if message.created_at else "",
        }
