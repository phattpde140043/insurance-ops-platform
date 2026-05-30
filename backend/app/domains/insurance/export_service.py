import csv
from io import StringIO

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.model_mixins import new_id
from app.core.storage import get_storage_provider
from app.domains.insurance.claim_lifecycle_service import ClaimLifecycleService
from app.domains.shared.file_service import FileService, FileUploadCreate
from app.domains.shared.job_service import BackgroundJobService, BackgroundJobType
from app.domains.shared.models import ExportArtifact
from app.domains.shared.repositories import ExportArtifactRepository


class ClaimExportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.claims = ClaimLifecycleService(session)
        self.artifacts = ExportArtifactRepository(session)
        self.jobs = BackgroundJobService(session)

    async def request_claim_export(
        self,
        *,
        organization_id: str,
        claim_id: str,
        actor_user_id: str,
        role: str,
    ) -> dict:
        await self._ensure_claim_access(organization_id, claim_id, actor_user_id, role)
        artifact = ExportArtifact(
            id=new_id("export"),
            organization_id=organization_id,
            artifact_type="claim_detail_history_csv",
            resource_type="insurance_claim",
            resource_id=claim_id,
            status="queued",
            requested_by_user_id=actor_user_id,
        )
        await self.artifacts.add(artifact)
        await self.jobs.create_job(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            job_type=BackgroundJobType.EXPORT_GENERATE.value,
            resource_type="export_artifact",
            resource_id=artifact.id,
            payload={"artifact_id": artifact.id},
        )
        return self._serialize(artifact)

    async def process_export_job(
        self, *, organization_id: str, artifact_id: str
    ) -> None:
        artifact = await self._get_artifact(organization_id, artifact_id)
        if artifact.status == "ready":
            return
        artifact.status = "processing"
        await self.session.commit()
        claim = await self.claims._get_claim(organization_id, artifact.resource_id)
        history = await self.claims.transitions.list_for_claim(
            organization_id, claim.id, limit=100
        )
        content = self._render_claim_csv(claim, history).encode("utf-8")
        asset = await FileService(
            self.session, get_storage_provider()
        ).create_file_asset(
            FileUploadCreate(
                organization_id=organization_id,
                created_by_user_id=artifact.requested_by_user_id,
                original_name=f"{claim.id}-history.csv",
                mime_type="text/csv",
                content=content,
            )
        )
        artifact.file_asset_id = asset.id
        artifact.status = "ready"
        await self.session.commit()

    async def get_artifact(
        self,
        *,
        organization_id: str,
        artifact_id: str,
        actor_user_id: str,
        role: str,
    ) -> dict:
        artifact = await self._get_artifact(organization_id, artifact_id)
        await self._ensure_claim_access(
            organization_id, artifact.resource_id, actor_user_id, role
        )
        return self._serialize(artifact)

    async def create_download_reference(
        self,
        *,
        organization_id: str,
        artifact_id: str,
        actor_user_id: str,
        role: str,
    ) -> dict:
        artifact = await self._get_artifact(organization_id, artifact_id)
        await self._ensure_claim_access(
            organization_id, artifact.resource_id, actor_user_id, role
        )
        if artifact.status != "ready" or artifact.file_asset_id is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "export_not_ready", "message": "Export artifact is not ready."},
            )
        return await FileService(
            self.session, get_storage_provider()
        ).create_download_reference(
            organization_id=organization_id,
            file_asset_id=artifact.file_asset_id,
            proxy_path=f"{settings.api_prefix}/insurance/exports/downloads/content",
        )

    async def _ensure_claim_access(
        self, organization_id: str, claim_id: str, actor_user_id: str, role: str
    ) -> None:
        claim = await self.claims._get_claim(organization_id, claim_id)
        await self.claims._ensure_read_access(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            role=role,
            claim=claim,
        )

    async def _get_artifact(
        self, organization_id: str, artifact_id: str
    ) -> ExportArtifact:
        artifact = await self.artifacts.get_for_org(organization_id, artifact_id)
        if artifact is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "export_not_found", "message": "Export artifact was not found."},
            )
        return artifact

    def _render_claim_csv(self, claim, history: list) -> str:
        stream = StringIO()
        writer = csv.writer(stream)
        writer.writerow(["claim_id", "customer_id", "incident_type", "claim_state"])
        writer.writerow([claim.id, claim.customer_id, claim.incident_type, claim.claim_state])
        writer.writerow([])
        writer.writerow(["from_state", "to_state", "created_at"])
        for transition in history:
            writer.writerow(
                [
                    transition.from_state or "",
                    transition.to_state,
                    transition.created_at.isoformat() if transition.created_at else "",
                ]
            )
        return stream.getvalue()

    def _serialize(self, artifact: ExportArtifact) -> dict:
        return {
            "id": artifact.id,
            "organization_id": artifact.organization_id,
            "artifact_type": artifact.artifact_type,
            "resource_type": artifact.resource_type,
            "resource_id": artifact.resource_id,
            "status": artifact.status,
            "file_asset_id": artifact.file_asset_id,
            "created_at": artifact.created_at.isoformat() if artifact.created_at else "",
        }
