import pytest

from app.domains.ai.retrieval_service import KnowledgeRetrievalService


class FakeSession:
    async def scalars(self, _statement):
        raise AssertionError("empty queries should not hit storage")


@pytest.mark.asyncio
async def test_empty_retrieval_query_returns_no_items() -> None:
    service = KnowledgeRetrievalService(FakeSession())
    result = await service.search(organization_id="org_demo", query="   ")
    assert result == {"items": []}

