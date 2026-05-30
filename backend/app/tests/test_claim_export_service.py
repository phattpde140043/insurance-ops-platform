from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.domains.insurance import export_service
from app.domains.insurance.export_service import ClaimExportService


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.commit_count = 0

    def add(self, record) -> None:
        self.added.append(record)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        self.commit_count += 1


class FakeStorage:
    def __init__(self) -> None:
        self.objects = {}

    async def put_bytes(self, key: str, content: bytes) -> None:
        self.objects[key] = content

    async def create_download_url(self, _key: str, *, expires_seconds: int):
        return None


class FakeArtifacts:
    def __init__(self) -> None:
        self.records = []

    async def add(self, artifact):
        self.records.append(artifact)
        return artifact

    async def get_for_org(self, organization_id: str, artifact_id: str):
        return next(
            (
                artifact
                for artifact in self.records
                if artifact.organization_id == organization_id and artifact.id == artifact_id
            ),
            None,
        )


class FakeTransitions:
    async def list_for_claim(self, _organization_id: str, _claim_id: str, *, limit: int):
        return [
            SimpleNamespace(
                from_state="reported",
                to_state="triage",
                created_at=None,
            )
        ]


class FakeClaims:
    def __init__(self) -> None:
        self.claim = SimpleNamespace(
            id="incident_1",
            organization_id="org_demo",
            customer_id="customer_1",
            incident_type="medical",
            claim_state="triage",
        )
        self.transitions = FakeTransitions()

    async def _get_claim(self, organization_id: str, claim_id: str):
        assert organization_id == "org_demo"
        assert claim_id == self.claim.id
        return self.claim

    async def _ensure_read_access(self, **_kwargs) -> None:
        pass


class FakeJobs:
    def __init__(self) -> None:
        self.created = []

    async def create_job(self, **kwargs):
        self.created.append(kwargs)
        return SimpleNamespace(id="job_export")


def build_service() -> ClaimExportService:
    service = ClaimExportService.__new__(ClaimExportService)
    service.session = FakeSession()
    service.claims = FakeClaims()
    service.artifacts = FakeArtifacts()
    service.jobs = FakeJobs()
    return service


@pytest.mark.asyncio
async def test_claim_export_request_enqueues_background_generation() -> None:
    service = build_service()

    artifact = await service.request_claim_export(
        organization_id="org_demo",
        claim_id="incident_1",
        actor_user_id="user_employee",
        role="employee",
    )

    assert artifact["status"] == "queued"
    assert service.jobs.created[0]["job_type"] == "export_generate"


@pytest.mark.asyncio
async def test_worker_generation_stores_real_csv_asset(monkeypatch) -> None:
    storage = FakeStorage()
    monkeypatch.setattr(export_service, "get_storage_provider", lambda: storage)
    service = build_service()
    artifact = await service.request_claim_export(
        organization_id="org_demo",
        claim_id="incident_1",
        actor_user_id="user_employee",
        role="employee",
    )

    await service.process_export_job(
        organization_id="org_demo",
        artifact_id=artifact["id"],
    )

    stored_artifact = service.artifacts.records[0]
    assert stored_artifact.status == "ready"
    assert stored_artifact.file_asset_id is not None
    assert b"claim_id,customer_id,incident_type,claim_state" in next(
        iter(storage.objects.values())
    )


@pytest.mark.asyncio
async def test_cross_tenant_export_metadata_is_not_visible() -> None:
    service = build_service()
    artifact = await service.request_claim_export(
        organization_id="org_demo",
        claim_id="incident_1",
        actor_user_id="user_employee",
        role="employee",
    )

    with pytest.raises(HTTPException) as exc:
        await service.get_artifact(
            organization_id="org_other",
            artifact_id=artifact["id"],
            actor_user_id="user_employee",
            role="employee",
        )

    assert exc.value.status_code == 404
