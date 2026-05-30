from datetime import UTC, datetime, timedelta

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
from app.domains.shared.outbox_service import DomainOutboxService
from app.domains.shared.idempotency_service import IdempotencyService


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
        self.outbox = DomainOutboxService(session)
        self.idempotency = IdempotencyService(session)

    async def create_appointment(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        idempotency_key: str,
        payload: CreateAppointmentIn,
    ) -> dict:
        reservation = await self.idempotency.reserve(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name="insurance.create_appointment",
            idempotency_key=idempotency_key,
            fingerprint_payload=payload.model_dump(),
        )
        if reservation.replayed and reservation.record.resource_id:
            existing = await self.appointments.get_for_org(
                organization_id, reservation.record.resource_id
            )
            if existing is not None:
                return self._serialize_appointment(existing)
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
        await self._emit(
            organization_id=organization_id,
            event_type="AppointmentRequested",
            aggregate_type="insurance_appointment",
            aggregate_id=appointment.id,
            payload={"customer_id": payload.customer_id},
        )
        self.idempotency.complete(
            reservation,
            resource_type="insurance_appointment",
            resource_id=appointment.id,
        )
        await self.session.commit()
        return self._serialize_appointment(appointment)

    async def create_conversation(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        idempotency_key: str,
        payload: CreateConversationIn,
    ) -> dict:
        reservation = await self.idempotency.reserve(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name="insurance.create_conversation",
            idempotency_key=idempotency_key,
            fingerprint_payload=payload.model_dump(),
        )
        if reservation.replayed and reservation.record.resource_id:
            existing = await self.conversations.get_for_org(
                organization_id, reservation.record.resource_id
            )
            if existing is not None:
                return self._serialize_conversation(existing)
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
        await self._emit(
            organization_id=organization_id,
            event_type="SupportConversationStarted",
            aggregate_type="insurance_conversation",
            aggregate_id=conversation.id,
            payload={"customer_id": payload.customer_id, "claim_id": payload.claim_id},
        )
        self.idempotency.complete(
            reservation,
            resource_type="insurance_conversation",
            resource_id=conversation.id,
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
        idempotency_key: str,
    ) -> dict:
        reservation = await self.idempotency.reserve(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name="insurance.open_claim_conversation",
            idempotency_key=idempotency_key,
            fingerprint_payload={"claim_id": claim_id},
        )
        if reservation.replayed and reservation.record.resource_id:
            replayed = await self.conversations.get_for_org(
                organization_id, reservation.record.resource_id
            )
            if replayed is not None:
                return self._serialize_conversation(replayed)
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
            self.idempotency.complete(
                reservation,
                resource_type="insurance_conversation",
                resource_id=existing.id,
            )
            await self.session.commit()
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
        await self._emit(
            organization_id=organization_id,
            event_type="SupportConversationStarted",
            aggregate_type="insurance_conversation",
            aggregate_id=conversation.id,
            payload={"customer_id": claim.customer_id, "claim_id": claim.id},
        )
        self.idempotency.complete(
            reservation,
            resource_type="insurance_conversation",
            resource_id=conversation.id,
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
        idempotency_key: str,
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
        reservation = await self.idempotency.reserve(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            command_name="insurance.send_support_message",
            idempotency_key=idempotency_key,
            fingerprint_payload={
                "conversation_id": conversation_id,
                "body": payload.body,
                "use_ai": payload.use_ai,
            },
        )
        if reservation.replayed and reservation.record.resource_id:
            existing = await self.messages.get_for_org(
                organization_id, reservation.record.resource_id
            )
            if existing is not None:
                return self._serialize_message(existing)
        message = InsuranceMessage(
            id=new_id("message"),
            organization_id=organization_id,
            conversation_id=conversation_id,
            sender_user_id=actor_user_id,
            role="employee" if role in {"admin", "employee"} else "user",
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
            handoff_reason = self._handoff_reason(payload.body, ai_response)
            if handoff_reason is not None:
                conversation.needs_human = True
                conversation.handoff_reason = handoff_reason
                conversation.priority = "high"
                conversation.due_at = (
                    datetime.now(UTC) + timedelta(hours=4)
                ).isoformat()
        elif role in {"admin", "employee"}:
            conversation.needs_human = False
            conversation.handoff_reason = None
            if role == "employee":
                conversation.employee_user_id = actor_user_id
        await self._emit(
            organization_id=organization_id,
            event_type="SupportMessageSent",
            aggregate_type="insurance_conversation",
            aggregate_id=conversation_id,
            payload={"message_id": message.id, "body_length": len(payload.body)},
        )
        self.idempotency.complete(
            reservation,
            resource_type="insurance_message",
            resource_id=message.id,
            response_metadata={
                "conversation_id": conversation_id,
                "body_length": len(payload.body),
            },
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
        offset: int = 0,
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
            organization_id,
            conversation_id,
            limit=self._bounded_limit(limit),
            offset=max(offset, 0),
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
        return min(max(limit, 1), 101)

    def _handoff_reason(self, message: str, ai_response: dict) -> str | None:
        normalized = message.lower()
        if any(
            phrase in normalized
            for phrase in ("human", "employee", "agent", "representative", "call me")
        ):
            return "customer_requested_human"
        if not ai_response["citations"]:
            return "ai_no_source"
        if ai_response["confidence"] < 0.5:
            return "low_confidence"
        return None

    async def _emit(
        self,
        *,
        organization_id: str,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: dict,
    ) -> None:
        outbox = getattr(self, "outbox", None)
        if outbox is not None:
            await outbox.append(
                organization_id=organization_id,
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                producer_module="insurance",
                payload=payload,
            )

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
            "needs_human": getattr(conversation, "needs_human", False),
            "handoff_reason": getattr(conversation, "handoff_reason", None),
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
