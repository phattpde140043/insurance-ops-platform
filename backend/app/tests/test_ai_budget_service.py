import pytest
from fastapi import HTTPException

from app.domains.ai import budget_service
from app.domains.ai.budget_service import AiBudgetService


class FakeSession:
    async def flush(self) -> None:
        pass


class FakeWindowRepository:
    def __init__(self) -> None:
        self.windows = {}

    async def get_window(self, **kwargs):
        key = (
            kwargs["organization_id"],
            kwargs["subject_type"],
            kwargs["subject_id"],
            kwargs["capability"],
            kwargs["window_started_at"],
        )
        return self.windows.get(key)

    async def add(self, window):
        key = (
            window.organization_id,
            window.subject_type,
            window.subject_id,
            window.capability,
            window.window_started_at,
        )
        self.windows[key] = window
        return window


def build_service() -> AiBudgetService:
    service = AiBudgetService(FakeSession())  # type: ignore[arg-type]
    service.windows = FakeWindowRepository()  # type: ignore[assignment]
    return service


@pytest.mark.asyncio
async def test_ai_budget_rejects_user_over_limit(monkeypatch) -> None:
    monkeypatch.setattr(budget_service.settings, "ai_user_requests_per_minute", 1)
    service = build_service()

    await service.consume(
        organization_id="org_demo", user_id="user_1", capability="chat"
    )
    with pytest.raises(HTTPException) as exc:
        await service.consume(
            organization_id="org_demo", user_id="user_1", capability="chat"
        )

    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "ai_budget_exceeded"


@pytest.mark.asyncio
async def test_ai_budget_rejects_tenant_over_limit(monkeypatch) -> None:
    monkeypatch.setattr(budget_service.settings, "ai_user_requests_per_minute", 5)
    monkeypatch.setattr(budget_service.settings, "ai_tenant_requests_per_minute", 1)
    service = build_service()

    await service.consume(
        organization_id="org_demo", user_id="user_1", capability="retrieval"
    )
    with pytest.raises(HTTPException) as exc:
        await service.consume(
            organization_id="org_demo", user_id="user_2", capability="retrieval"
        )

    assert exc.value.status_code == 429
