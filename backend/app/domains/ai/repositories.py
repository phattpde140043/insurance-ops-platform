from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.repository import BaseRepository
from app.domains.ai.models import (
    AiProviderCall,
    ChatMessage,
    ChatSession,
    KnowledgeBase,
    KnowledgeChunk,
    KnowledgeDocument,
)


class AiProviderCallRepository(BaseRepository[AiProviderCall]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AiProviderCall)


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


class ChatSessionRepository(BaseRepository[ChatSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ChatSession)


class ChatMessageRepository(BaseRepository[ChatMessage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ChatMessage)
