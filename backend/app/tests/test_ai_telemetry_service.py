import pytest

from app.domains.ai import telemetry_service
from app.domains.ai.telemetry_service import AiOperationalTelemetryService


class ScalarResult:
    def one(self):
        return (7, 125.8, 2)


class FakeSession:
    async def scalar(self, _statement):
        return 3

    async def execute(self, _statement):
        return ScalarResult()


@pytest.mark.asyncio
async def test_ai_operations_exposes_redacted_saturation_metrics(monkeypatch) -> None:
    monkeypatch.setattr(
        telemetry_service,
        "get_ai_pool_status",
        lambda: {"checked_out": 4, "size": 3, "overflow": 1},
    )
    service = AiOperationalTelemetryService(FakeSession())  # type: ignore[arg-type]

    result = await service.get_summary(organization_id="org_demo")

    assert result["queue_depth"] == 3
    assert result["provider_calls"] == 7
    assert result["average_provider_latency_ms"] == 125
    assert result["provider_timeout_count"] == 2
    assert result["pool"]["saturated"] is True
    assert "prompt" not in str(result).lower()


def test_ai_session_factory_is_isolated_from_core_pool() -> None:
    from app.core.database import AiAsyncSessionLocal, AsyncSessionLocal

    assert AiAsyncSessionLocal is not AsyncSessionLocal
