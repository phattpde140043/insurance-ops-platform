from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.domains.ai.models import ChatMessage, ChatSession
from app.domains.ai.repositories import ChatMessageRepository, ChatSessionRepository
from app.domains.ai.retrieval_service import KnowledgeRetrievalService


class GuardedChatbotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sessions = ChatSessionRepository(session)
        self.messages = ChatMessageRepository(session)
        self.retrieval = KnowledgeRetrievalService(session)

    async def answer(
        self, *, organization_id: str, user_id: str, message: str
    ) -> dict:
        session = ChatSession(
            id=new_id("chat"),
            organization_id=organization_id,
            user_id=user_id,
            status="open",
        )
        await self.sessions.add(session)
        await self.messages.add(
            ChatMessage(
                id=new_id("chatmsg"),
                organization_id=organization_id,
                session_id=session.id,
                user_id=user_id,
                role="user",
                body=message,
                citations={},
            )
        )

        retrieval = await self.retrieval.search(
            organization_id=organization_id,
            query=message,
            limit=3,
        )
        chunks = retrieval["items"]
        if not chunks:
            answer = (
                "I could not find an answer in the company's knowledge base. "
                "Please contact a support employee for help."
            )
            citations: list[str] = []
            confidence = 0.0
        else:
            citations = [chunk["chunk_id"] for chunk in chunks]
            answer = (
                "Based on the company knowledge base: "
                + " ".join(chunk["content"] for chunk in chunks[:2])
            )
            confidence = max(chunk["score"] for chunk in chunks)

        await self.messages.add(
            ChatMessage(
                id=new_id("chatmsg"),
                organization_id=organization_id,
                session_id=session.id,
                user_id=None,
                role="assistant",
                body=answer,
                citations={"chunk_ids": citations},
            )
        )
        await self.session.commit()
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
        }

