from datetime import UTC, datetime

import pytest

from app.domains.shared.models import BackgroundJob, DomainOutboxEvent
from app.workers import background_worker


class FakeSession:
    def __init__(self) -> None:
        self.rollback_count = 0

    async def rollback(self) -> None:
        self.rollback_count += 1


class FakeJobService:
    def __init__(self, job: BackgroundJob) -> None:
        self.job = job
        self.completed: list[str] = []
        self.failed: list[str] = []

    async def claim_next_batch(self, **_kwargs) -> list[BackgroundJob]:
        return [self.job]

    async def mark_completed(self, **kwargs) -> None:
        self.completed.append(kwargs["job_id"])

    async def mark_failed(self, **kwargs) -> None:
        self.failed.append(kwargs["job_id"])


class FakeOutboxService:
    def __init__(self, events: list[DomainOutboxEvent] | None = None) -> None:
        self.events = events or []
        self.published: list[str] = []
        self.failed: list[str] = []

    async def claim_next_batch(self, **_kwargs) -> list[DomainOutboxEvent]:
        return self.events

    async def mark_published(self, event: DomainOutboxEvent) -> None:
        self.published.append(event.id)

    async def mark_failed(self, event: DomainOutboxEvent, _error: str) -> None:
        self.failed.append(event.id)


def build_ingest_job(job_type: str = "knowledge_ingest") -> BackgroundJob:
    return BackgroundJob(
        id="job_ingest",
        organization_id="org_demo",
        job_type=job_type,
        status="processing",
        attempts=1,
        payload={"document_id": "knowledge_1", "actor_user_id": "user_admin"},
        available_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_worker_processes_knowledge_ingest_job(monkeypatch) -> None:
    processed: list[str] = []

    class FakeKnowledgeService:
        def __init__(self, _session) -> None:
            pass

        async def process_ingest_job(self, **kwargs) -> None:
            processed.append(kwargs["document_id"])

    monkeypatch.setattr(background_worker, "KnowledgeDocumentService", FakeKnowledgeService)
    session = FakeSession()
    worker = background_worker.BackgroundWorker(session)  # type: ignore[arg-type]
    worker.outbox = FakeOutboxService()  # type: ignore[assignment]
    worker.job_service = FakeJobService(build_ingest_job())  # type: ignore[assignment]

    assert await worker.run_once() is True
    assert processed == ["knowledge_1"]
    assert worker.job_service.completed == ["job_ingest"]


@pytest.mark.asyncio
async def test_worker_rolls_back_partial_ingest_and_marks_document_failed(
    monkeypatch,
) -> None:
    failed_documents: list[str] = []

    class FakeKnowledgeService:
        def __init__(self, _session) -> None:
            pass

        async def process_ingest_job(self, **_kwargs) -> None:
            raise RuntimeError("extraction failed")

        async def mark_ingest_failed(self, **kwargs) -> None:
            failed_documents.append(kwargs["document_id"])

    monkeypatch.setattr(background_worker, "KnowledgeDocumentService", FakeKnowledgeService)
    session = FakeSession()
    worker = background_worker.BackgroundWorker(session)  # type: ignore[arg-type]
    worker.outbox = FakeOutboxService()  # type: ignore[assignment]
    worker.job_service = FakeJobService(build_ingest_job())  # type: ignore[assignment]

    assert await worker.run_once() is True
    assert session.rollback_count == 1
    assert failed_documents == ["knowledge_1"]
    assert worker.job_service.failed == ["job_ingest"]


@pytest.mark.asyncio
async def test_worker_dispatches_outbox_event_before_background_job() -> None:
    event = DomainOutboxEvent(
        id="event_1",
        organization_id="org_demo",
        event_type="IncidentReported",
        aggregate_type="insurance_claim",
        aggregate_id="incident_1",
        producer_module="insurance",
        payload_json={},
        status="processing",
        attempts=1,
        available_at=datetime.now(UTC),
    )
    dispatched: list[str] = []

    class FakeDispatcher:
        async def dispatch(self, queued_event: DomainOutboxEvent) -> None:
            dispatched.append(queued_event.id)

    session = FakeSession()
    worker = background_worker.BackgroundWorker(session)  # type: ignore[arg-type]
    worker.outbox = FakeOutboxService([event])  # type: ignore[assignment]
    worker.dispatcher = FakeDispatcher()  # type: ignore[assignment]

    assert await worker.run_once() is True
    assert dispatched == ["event_1"]
    assert worker.outbox.published == ["event_1"]


@pytest.mark.asyncio
async def test_worker_runs_dashboard_reconciliation_job(monkeypatch) -> None:
    reconciled: list[str] = []

    class FakeProjectionService:
        def __init__(self, _session) -> None:
            pass

        async def apply_event(self, _event) -> None:
            pass

        async def reconcile(self, organization_id: str) -> None:
            reconciled.append(organization_id)

    monkeypatch.setattr(
        background_worker, "DashboardProjectionService", FakeProjectionService
    )
    session = FakeSession()
    worker = background_worker.BackgroundWorker(session)  # type: ignore[arg-type]
    worker.outbox = FakeOutboxService()  # type: ignore[assignment]
    worker.job_service = FakeJobService(  # type: ignore[assignment]
        build_ingest_job("dashboard_reconcile")
    )

    assert await worker.run_once() is True
    assert reconciled == ["org_demo"]
    assert worker.job_service.completed == ["job_ingest"]


@pytest.mark.asyncio
async def test_worker_generates_export_artifact(monkeypatch) -> None:
    generated: list[str] = []

    class FakeExportService:
        def __init__(self, _session) -> None:
            pass

        async def process_export_job(self, **kwargs) -> None:
            generated.append(kwargs["artifact_id"])

    monkeypatch.setattr(background_worker, "ClaimExportService", FakeExportService)
    job = build_ingest_job("export_generate")
    job.payload = {"artifact_id": "export_1"}
    session = FakeSession()
    worker = background_worker.BackgroundWorker(session)  # type: ignore[arg-type]
    worker.outbox = FakeOutboxService()  # type: ignore[assignment]
    worker.job_service = FakeJobService(job)  # type: ignore[assignment]

    assert await worker.run_once() is True
    assert generated == ["export_1"]
