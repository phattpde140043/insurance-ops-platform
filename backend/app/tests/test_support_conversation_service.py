from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.domains.insurance.schemas import CreateMessageIn
from app.domains.insurance.support_service import InsuranceSupportService


class FakeConversationRepository:
    def __init__(self, conversations) -> None:
        self.conversations = conversations

    async def list_for_org(self, organization_id: str, *, limit: int = 50, offset: int = 0):
        return [
            conversation
            for conversation in self.conversations
            if conversation.organization_id == organization_id
        ][offset : offset + limit]

    async def list_for_customer(
        self, organization_id: str, customer_id: str, *, limit: int = 10
    ):
        return [
            conversation
            for conversation in self.conversations
            if conversation.organization_id == organization_id
            and conversation.customer_id == customer_id
        ][:limit]

    async def list_visible_for_employee(
        self,
        organization_id: str,
        employee_user_id: str,
        customer_ids: set[str],
        *,
        limit: int = 25,
    ):
        return [
            conversation
            for conversation in self.conversations
            if conversation.organization_id == organization_id
            and (
                conversation.employee_user_id == employee_user_id
                or conversation.customer_id in customer_ids
            )
        ][:limit]

    async def get_for_org(self, organization_id: str, conversation_id: str):
        for conversation in self.conversations:
            if (
                conversation.organization_id == organization_id
                and conversation.id == conversation_id
            ):
                return conversation
        return None

    async def get_open_for_claim(self, organization_id: str, claim_id: str):
        for conversation in self.conversations:
            if (
                conversation.organization_id == organization_id
                and conversation.claim_id == claim_id
                and conversation.status == "open"
            ):
                return conversation
        return None

    async def add(self, conversation):
        self.conversations.append(conversation)
        return conversation


class FakeMessageRepository:
    def __init__(self, messages) -> None:
        self.messages = messages

    async def list_for_conversation(
        self,
        organization_id: str,
        conversation_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ):
        return [
            message
            for message in self.messages
            if message.organization_id == organization_id
            and message.conversation_id == conversation_id
        ][offset : offset + limit]

    async def add(self, message):
        self.messages.append(message)
        return message

    async def get_for_org(self, organization_id: str, message_id: str):
        for message in self.messages:
            if message.organization_id == organization_id and message.id == message_id:
                return message
        return None


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


class FakeClaimRepository:
    async def get_for_org(self, organization_id: str, claim_id: str):
        if organization_id == "org_demo" and claim_id == "incident_1":
            return SimpleNamespace(id=claim_id, customer_id="customer_lan")
        return None


class FakeAuditLog:
    def __init__(self) -> None:
        self.events = []

    async def record(self, event):
        self.events.append(event)
        return event


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


class FakeIdempotency:
    def __init__(self) -> None:
        self.replayed = False
        self.record = SimpleNamespace(resource_id=None)

    async def reserve(self, **_kwargs):
        return SimpleNamespace(replayed=self.replayed, record=self.record)

    def complete(self, *_args, **kwargs) -> None:
        self.record.resource_id = kwargs["resource_id"]
        self.replayed = True


class FakeChatbot:
    async def answer(self, *, organization_id: str, user_id: str, message: str):
        return {
            "answer": "I could not find an answer in the company's knowledge base.",
            "citations": [],
            "confidence": 0.0,
        }


def build_conversation(conversation_id: str, customer_id: str, employee_user_id=None):
    return SimpleNamespace(
        id=conversation_id,
        organization_id="org_demo",
        customer_id=customer_id,
        employee_user_id=employee_user_id,
        claim_id=None,
        status="open",
        created_at=None,
    )


def build_message(message_id: str, conversation_id: str):
    return SimpleNamespace(
        id=message_id,
        organization_id="org_demo",
        conversation_id=conversation_id,
        sender_user_id="user_customer",
        role="user",
        body="Need help",
        citations_json={"chunk_ids": []},
        created_at=None,
    )


def build_service(conversations, messages) -> InsuranceSupportService:
    service = InsuranceSupportService.__new__(InsuranceSupportService)
    service.session = FakeSession()
    service.conversations = FakeConversationRepository(conversations)
    service.messages = FakeMessageRepository(messages)
    service.assignments = FakeAssignments()
    service.customers = FakeCustomers()
    service.claims = FakeClaimRepository()
    service.chatbot = FakeChatbot()
    service.audit_log = FakeAuditLog()
    service.idempotency = FakeIdempotency()
    return service


@pytest.mark.asyncio
async def test_customer_only_lists_own_conversations() -> None:
    service = build_service(
        [
            build_conversation("conversation_1", "customer_lan"),
            build_conversation("conversation_2", "customer_other"),
        ],
        [],
    )

    result = await service.list_conversations(
        organization_id="org_demo",
        actor_user_id="user_customer",
        role="customer",
    )

    assert [item["id"] for item in result] == ["conversation_1"]


@pytest.mark.asyncio
async def test_employee_only_reads_assigned_customer_conversation() -> None:
    service = build_service(
        [
            build_conversation("conversation_1", "customer_lan"),
            build_conversation("conversation_2", "customer_other"),
        ],
        [build_message("message_1", "conversation_1")],
    )

    detail = await service.get_conversation_detail(
        organization_id="org_demo",
        actor_user_id="user_employee",
        role="employee",
        conversation_id="conversation_1",
    )

    assert detail["id"] == "conversation_1"
    assert detail["messages"][0]["id"] == "message_1"

    with pytest.raises(HTTPException) as exc:
        await service.get_conversation_detail(
            organization_id="org_demo",
            actor_user_id="user_employee",
            role="employee",
            conversation_id="conversation_2",
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_message_history_is_bounded_and_create_requires_access() -> None:
    service = build_service(
        [build_conversation("conversation_1", "customer_lan")],
        [
            build_message("message_1", "conversation_1"),
            build_message("message_2", "conversation_1"),
        ],
    )

    messages = await service.list_messages(
        organization_id="org_demo",
        actor_user_id="user_customer",
        role="customer",
        conversation_id="conversation_1",
        limit=1,
    )
    created = await service.create_message(
        organization_id="org_demo",
        actor_user_id="user_customer",
        role="customer",
        conversation_id="conversation_1",
        idempotency_key="message-1",
        payload=CreateMessageIn(body="Adding context"),
    )

    assert [message["id"] for message in messages] == ["message_1"]
    assert created["body"] == "Adding context"
    assert service.session.committed


@pytest.mark.asyncio
async def test_ai_response_is_persisted_in_same_conversation() -> None:
    service = build_service([build_conversation("conversation_1", "customer_lan")], [])

    await service.create_message(
        organization_id="org_demo",
        actor_user_id="user_customer",
        role="customer",
        conversation_id="conversation_1",
        idempotency_key="message-ai-1",
        payload=CreateMessageIn(body="What is covered?", use_ai=True),
    )

    stored_messages = service.messages.messages
    assert [message.role for message in stored_messages] == ["user", "assistant"]
    assert stored_messages[1].conversation_id == "conversation_1"
    assert stored_messages[1].citations_json == {"chunk_ids": []}
    assert service.conversations.conversations[0].needs_human is True
    assert service.conversations.conversations[0].handoff_reason == "ai_no_source"


@pytest.mark.asyncio
async def test_employee_reply_clears_handoff_in_same_conversation() -> None:
    conversation = build_conversation("conversation_1", "customer_lan", "user_employee")
    conversation.needs_human = True
    conversation.handoff_reason = "ai_no_source"
    service = build_service([conversation], [])

    message = await service.create_message(
        organization_id="org_demo",
        actor_user_id="user_employee",
        role="employee",
        conversation_id="conversation_1",
        idempotency_key="employee-reply-1",
        payload=CreateMessageIn(body="I can help with this."),
    )

    assert message["role"] == "employee"
    assert conversation.needs_human is False
    assert conversation.employee_user_id == "user_employee"


@pytest.mark.asyncio
async def test_duplicate_ai_retry_does_not_duplicate_assistant_message() -> None:
    service = build_service([build_conversation("conversation_1", "customer_lan")], [])

    for _attempt in range(2):
        await service.create_message(
            organization_id="org_demo",
            actor_user_id="user_customer",
            role="customer",
            conversation_id="conversation_1",
            idempotency_key="message-ai-retry",
            payload=CreateMessageIn(body="What is covered?", use_ai=True),
        )

    assert [message.role for message in service.messages.messages] == [
        "user",
        "assistant",
    ]


@pytest.mark.asyncio
async def test_open_claim_conversation_creates_claim_linked_thread() -> None:
    service = build_service([], [])

    result = await service.open_claim_conversation(
        organization_id="org_demo",
        actor_user_id="user_employee",
        role="employee",
        claim_id="incident_1",
        idempotency_key="claim-conversation-1",
    )

    assert result["claim_id"] == "incident_1"
    assert result["customer_id"] == "customer_lan"
    assert service.conversations.conversations[0].claim_id == "incident_1"
    assert service.audit_log.events[0].action == "insurance.claim_conversation_opened"
