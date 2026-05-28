from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_mixins import new_id
from app.core.storage import LocalStorageProvider, StorageProvider
from fastapi import HTTPException, status

from app.domains.ai.models import KnowledgeChunk, KnowledgeDocument
from app.domains.ai.repositories import KnowledgeChunkRepository, KnowledgeDocumentRepository
from app.domains.ai.pdf_extraction import PdfExtractionService, chunk_text
from app.domains.ai.schemas import CreateKnowledgeDocumentIn
from app.domains.ai.vector_store import LocalHashEmbeddingReferenceProvider
from app.domains.platform.audit_service import AuditEventCreate, AuditLogService
from app.domains.shared.file_service import FileService, FileUploadCreate
from app.domains.shared.job_service import BackgroundJobService, BackgroundJobType
from app.domains.shared.repositories import FileAssetRepository


class KnowledgeDocumentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.documents = KnowledgeDocumentRepository(session)
        self.chunks = KnowledgeChunkRepository(session)
        self.files = FileAssetRepository(session)
        self.audit_log = AuditLogService(session)
        self.jobs = BackgroundJobService(session)
        self.embeddings = LocalHashEmbeddingReferenceProvider()

    async def list_documents(self, organization_id: str, *, limit: int = 50) -> list[dict]:
        documents = await self.documents.list_recent_for_org(
            organization_id,
            limit=limit,
        )
        return [self._serialize(document) for document in documents]

    async def create_document(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        payload: CreateKnowledgeDocumentIn,
        file_asset_id: str | None = None,
    ) -> dict:
        document = KnowledgeDocument(
            id=new_id("knowledge"),
            organization_id=organization_id,
            title=payload.title,
            source_type=payload.source_type,
            file_asset_id=file_asset_id,
            status="uploaded",
        )
        await self.documents.add(document)
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="ai.knowledge_document_created",
                resource_type="knowledge_document",
                resource_id=document.id,
                metadata={"source_type": payload.source_type},
            )
        )
        await self.session.commit()
        return self._serialize(document)

    async def upload_document(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        title: str,
        source_type: str,
        file_name: str,
        mime_type: str,
        content: bytes,
        storage: StorageProvider,
    ) -> dict:
        file_service = FileService(self.session, storage)
        asset = await file_service.create_file_asset(
            FileUploadCreate(
                organization_id=organization_id,
                created_by_user_id=actor_user_id,
                original_name=file_name,
                mime_type=mime_type,
                content=content,
            )
        )
        return await self.create_document(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            payload=CreateKnowledgeDocumentIn(title=title, source_type=source_type),
            file_asset_id=asset.id,
        )

    async def ingest_document(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        document_id: str,
    ) -> dict:
        document = await self.documents.get_for_org(organization_id, document_id)
        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "knowledge_document_not_found",
                    "message": "Knowledge document was not found.",
                },
            )
        job = await self.jobs.create_job(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            job_type=BackgroundJobType.KNOWLEDGE_INGEST.value,
            resource_type="knowledge_document",
            resource_id=document.id,
            payload={"document_id": document.id},
        )
        chunk_contents = await self._extract_chunks(document)
        for index, content in enumerate(chunk_contents):
            await self.chunks.add(
                KnowledgeChunk(
                    id=new_id("chunk"),
                    organization_id=organization_id,
                    document_id=document.id,
                    chunk_index=index,
                    content=content,
                    embedding_ref=await self.embeddings.create_embedding_ref(
                        organization_id=organization_id,
                        content=content,
                    ),
                )
            )
        document.status = "ingested"
        await self.audit_log.record(
            AuditEventCreate(
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                action="ai.knowledge_document_ingested",
                resource_type="knowledge_document",
                resource_id=document.id,
                metadata={"background_job_id": job.id, "chunk_count": len(chunk_contents)},
            )
        )
        await self.session.commit()
        return {
            "status": "queued",
            "background_job_id": job.id,
            "chunk_count": len(chunk_contents),
        }

    async def _extract_chunks(self, document: KnowledgeDocument) -> list[str]:
        if document.file_asset_id:
            asset = await self.files.get_for_org(
                document.organization_id, document.file_asset_id
            )
            if asset and asset.mime_type == "application/pdf":
                content = await LocalStorageProvider().get_bytes(asset.storage_key)
                chunks = chunk_text(PdfExtractionService().extract_text(content))
                if chunks:
                    return chunks

        return [
            f"Placeholder extracted content for {document.title}. "
            "PDF extraction was unavailable for this document."
        ]

    def _serialize(self, document: KnowledgeDocument) -> dict:
        return {
            "id": document.id,
            "organization_id": document.organization_id,
            "title": document.title,
            "source_type": document.source_type,
            "status": document.status,
            "created_at": document.created_at.isoformat()
            if document.created_at
            else "",
        }
