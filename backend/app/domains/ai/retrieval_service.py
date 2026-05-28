from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import KnowledgeChunk


class KnowledgeRetrievalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def search(
        self, *, organization_id: str, query: str, limit: int = 5
    ) -> dict:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return {"items": []}

        result = await self.session.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.organization_id == organization_id)
            .limit(max(limit, 1))
        )
        chunks = []
        for chunk in result.all():
            content = chunk.content or ""
            if normalized_query in content.lower():
                score = 1.0
            else:
                query_terms = set(normalized_query.split())
                content_terms = set(content.lower().split())
                overlap = len(query_terms & content_terms)
                score = overlap / max(len(query_terms), 1)
            if score > 0:
                chunks.append(
                    {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "content": content,
                        "score": score,
                    }
                )

        chunks.sort(key=lambda item: item["score"], reverse=True)
        return {"items": chunks[:limit]}

