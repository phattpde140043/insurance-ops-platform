from datetime import UTC, datetime

import pytest

from app.domains.shared.job_service import BackgroundJobService, BackgroundJobStatus
from app.domains.shared.models import BackgroundJob


class FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def commit(self) -> None:
        self.commit_count += 1


class FakeJobRepository:
    def __init__(self, job: BackgroundJob) -> None:
        self.job = job
        self.claim_calls: list[dict] = []

    async def claim_next_batch(self, **kwargs) -> list[BackgroundJob]:
        self.claim_calls.append(kwargs)
        return [self.job]

    async def get_for_org(
        self, organization_id: str, job_id: str
    ) -> BackgroundJob | None:
        if self.job.organization_id == organization_id and self.job.id == job_id:
            return self.job
        return None


class FakeAuditLog:
    def __init__(self) -> None:
        self.events = []

    async def record(self, event) -> None:
        self.events.append(event)


def build_job(*, attempts: int = 0) -> BackgroundJob:
    return BackgroundJob(
        id="job_1",
        organization_id="org_demo",
        job_type="sla_evaluate",
        status=BackgroundJobStatus.PROCESSING.value,
        attempts=attempts,
        payload={},
        available_at=datetime.now(UTC),
        locked_by="worker-old",
        locked_until=datetime.now(UTC),
    )


def build_service(job: BackgroundJob) -> tuple[BackgroundJobService, FakeSession, FakeJobRepository, FakeAuditLog]:
    session = FakeSession()
    service = BackgroundJobService(session)  # type: ignore[arg-type]
    repository = FakeJobRepository(job)
    audit_log = FakeAuditLog()
    service.repository = repository  # type: ignore[assignment]
    service.audit_log = audit_log  # type: ignore[assignment]
    return service, session, repository, audit_log


@pytest.mark.asyncio
async def test_claim_next_batch_delegates_atomic_claim_and_commits() -> None:
    job = build_job()
    service, session, repository, _audit_log = build_service(job)

    claimed = await service.claim_next_batch(worker_id="worker-new", batch_size=1)

    assert claimed == [job]
    assert repository.claim_calls[0]["worker_id"] == "worker-new"
    assert repository.claim_calls[0]["batch_size"] == 1
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_mark_failed_schedules_retry_and_redacts_error(monkeypatch) -> None:
    job = build_job(attempts=1)
    service, _session, _repository, audit_log = build_service(job)
    monkeypatch.setattr("app.domains.shared.job_service.settings.worker_max_attempts", 3)
    monkeypatch.setattr(
        "app.domains.shared.job_service.settings.worker_retry_backoff_seconds", 0
    )

    await service.mark_failed(
        organization_id="org_demo",
        actor_user_id=None,
        job_id=job.id,
        error_message="x" * 800,
    )

    assert job.status == BackgroundJobStatus.QUEUED.value
    assert job.locked_by is None
    assert job.locked_until is None
    assert len(job.error_message or "") == 500
    assert audit_log.events[0].metadata == {"attempts": 1, "status": "queued"}


@pytest.mark.asyncio
async def test_mark_failed_poison_job_after_max_attempts(monkeypatch) -> None:
    job = build_job(attempts=3)
    service, _session, _repository, audit_log = build_service(job)
    monkeypatch.setattr("app.domains.shared.job_service.settings.worker_max_attempts", 3)

    await service.mark_failed(
        organization_id="org_demo",
        actor_user_id=None,
        job_id=job.id,
        error_message="provider unavailable",
    )

    assert job.status == BackgroundJobStatus.POISONED.value
    assert job.finished_at is not None
    assert audit_log.events[0].action == "background_job.poisoned"


@pytest.mark.asyncio
async def test_mark_completed_releases_worker_lock() -> None:
    job = build_job(attempts=1)
    service, _session, _repository, _audit_log = build_service(job)

    await service.mark_completed(
        organization_id="org_demo",
        actor_user_id=None,
        job_id=job.id,
    )

    assert job.status == BackgroundJobStatus.COMPLETED.value
    assert job.locked_by is None
    assert job.locked_until is None
    assert job.finished_at is not None
