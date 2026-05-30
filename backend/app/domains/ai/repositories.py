from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select

from app.core.repository import BaseRepository
from app.domains.ai.models import (
    AiProviderCall,
    AiRateLimitWindow,
    ChatMessage,
    ChatSession,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)


class AiProviderCallRepository(BaseRepository[AiProviderCall]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AiProviderCall)


class AiRateLimitWindowRepository(BaseRepository[AiRateLimitWindow]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AiRateLimitWindow)

    async def get_window(
        self,
        *,
        organization_id: str,
        subject_type: str,
        subject_id: str,
        capability: str,
        window_started_at,
    ) -> AiRateLimitWindow | None:
        return await self.session.scalar(
            select(AiRateLimitWindow)
            .where(
                AiRateLimitWindow.organization_id == organization_id,
                AiRateLimitWindow.subject_type == subject_type,
                AiRateLimitWindow.subject_id == subject_id,
                AiRateLimitWindow.capability == capability,
                AiRateLimitWindow.window_started_at == window_started_at,
            )
            .with_for_update()
        )


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, KnowledgeBase)


class KnowledgeDocumentRepository(BaseRepository[KnowledgeDocument]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, KnowledgeDocument)

    async def list_recent_for_org(
        self, organization_id: str, *, limit: int = 50
    ) -> list[KnowledgeDocument]:
        result = await self.session.scalars(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.organization_id == organization_id)
            .order_by(KnowledgeDocument.created_at.desc())
            .limit(limit)
        )
        return list(result.all())


class KnowledgeChunkRepository(BaseRepository[KnowledgeChunk]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, KnowledgeChunk)

    async def list_for_document(
        self, organization_id: str, document_id: str
    ) -> list[KnowledgeChunk]:
        result = await self.session.scalars(
            select(KnowledgeChunk)
            .where(
                KnowledgeChunk.organization_id == organization_id,
                KnowledgeChunk.document_id == document_id,
            )
            .order_by(KnowledgeChunk.chunk_index.asc())
        )
        return list(result.all())

    async def delete_for_document(self, organization_id: str, document_id: str) -> None:
        await self.session.execute(
            delete(KnowledgeChunk).where(
                KnowledgeChunk.organization_id == organization_id,
                KnowledgeChunk.document_id == document_id,
            )
        )


class ChatSessionRepository(BaseRepository[ChatSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ChatSession)


class ChatMessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ChatMessage)
