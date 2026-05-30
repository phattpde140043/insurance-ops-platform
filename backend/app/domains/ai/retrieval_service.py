from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.ai.models import KnowledgeChunk
from app.core.config import settings
from app.domains.ai.budget_service import AiBudgetService


class KnowledgeRetrievalService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.budget = AiBudgetService(session)

    async def search(
        self,
        *,
        organization_id: str,
        query: str,
        limit: int = 5,
        actor_user_id: str | None = None,
    ) -> dict:
        if len(query) > settings.ai_max_prompt_chars:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "ai_query_too_large",
                    "message": "Retrieval query exceeds the configured size limit.",
                },
            )
        if actor_user_id is not None:
            await self.budget.consume(
                organization_id=organization_id,
                user_id=actor_user_id,
                capability="retrieval",
            )
        limit = min(max(limit, 1), settings.ai_max_retrieved_chunks)
        normalized_query = query.strip().lower()
        if not normalized_query:
            return {"items": []}

        result = await self.session.scalars(
            select(KnowledgeChunk)
            .where(KnowledgeChunk.organization_id == organization_id)
            .limit(limit)
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
        if actor_user_id is not None:
            await self.session.commit()
        return {"items": chunks[:limit]}
