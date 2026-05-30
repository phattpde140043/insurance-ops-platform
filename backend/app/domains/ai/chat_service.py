import asyncio
from time import monotonic

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.model_mixins import new_id
from app.domains.ai.budget_service import AiBudgetService
from app.domains.ai.guardrail_service import SAFE_FALLBACK, SemanticGuardrailService
from app.domains.ai.models import ChatMessage, ChatSession
from app.domains.ai.repositories import ChatMessageRepository, ChatSessionRepository
from app.domains.ai.retrieval_service import KnowledgeRetrievalService


class GuardedChatbotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sessions = ChatSessionRepository(session)
        self.messages = ChatMessageRepository(session)
        self.retrieval = KnowledgeRetrievalService(session)
        self.budget = AiBudgetService(session)
        self.guardrails = SemanticGuardrailService()

    async def answer(
        self, *, organization_id: str, user_id: str, message: str
    ) -> dict:
        if len(message) > settings.ai_max_prompt_chars:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "ai_prompt_too_large",
                    "message": "AI prompt exceeds the configured size limit.",
                },
            )
        await self.budget.consume(
            organization_id=organization_id,
            user_id=user_id,
            capability="chat",
        )
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
        input_decision = self.guardrails.check_input(message)
        if not input_decision.allowed:
            await self._persist_assistant(
                organization_id=organization_id,
                session_id=session.id,
                answer=SAFE_FALLBACK,
                citations=[],
            )
            await self.budget.record_provider_call(
                organization_id=organization_id,
                capability="semantic-guardrail",
                status_value="blocked",
                latency_ms=0,
                cost_units=0,
                error_message=input_decision.reason,
            )
            await self.session.commit()
            return {"answer": SAFE_FALLBACK, "citations": [], "confidence": 0.0}

        started_at = monotonic()
        provider_status = "completed"
        provider_error = None
        try:
            retrieval = await asyncio.wait_for(
                self.retrieval.search(
                    organization_id=organization_id,
                    query=message,
                    limit=min(3, settings.ai_max_retrieved_chunks),
                ),
                timeout=settings.ai_provider_timeout_seconds,
            )
            chunks = retrieval["items"]
        except TimeoutError:
            chunks = []
            provider_status = "timeout"
            provider_error = "provider timeout"
        except Exception:
            chunks = []
            provider_status = "error"
            provider_error = "provider error"
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
        answer = answer[: settings.ai_max_response_chars]
        output_decision = self.guardrails.check_output(
            answer=answer,
            citations=citations,
            allowed_chunk_ids={chunk["chunk_id"] for chunk in chunks},
        )
        if not output_decision.allowed:
            answer = SAFE_FALLBACK
            citations = []
            confidence = 0.0
            provider_status = "guarded"
            provider_error = output_decision.reason

        await self.budget.record_provider_call(
            organization_id=organization_id,
            capability="chat-retrieval",
            status_value=provider_status,
            latency_ms=int((monotonic() - started_at) * 1000),
            cost_units=len(chunks),
            error_message=provider_error,
        )

        await self._persist_assistant(
            organization_id=organization_id,
            session_id=session.id,
            answer=answer,
            citations=citations,
        )
        await self.session.commit()
        return {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
        }

    async def _persist_assistant(
        self,
        *,
        organization_id: str,
        session_id: str,
        answer: str,
        citations: list[str],
    ) -> None:
        await self.messages.add(
            ChatMessage(
                id=new_id("chatmsg"),
                organization_id=organization_id,
                session_id=session_id,
                user_id=None,
                role="assistant",
                body=answer,
                citations={"chunk_ids": citations},
            )
        )
