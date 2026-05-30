import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, get_request_context, require_roles
from app.core.config import settings
from app.core.database import get_ai_db_session
from app.core.storage import get_storage_provider, verify_storage_download_token
from app.domains.ai.chat_service import GuardedChatbotService
from app.domains.ai.knowledge_service import KnowledgeDocumentService
from app.domains.ai.retrieval_service import KnowledgeRetrievalService
from app.domains.ai.telemetry_service import AiOperationalTelemetryService
from app.domains.ai.schemas import (
    AiOperationalTelemetryOut,
    ChatRequestIn,
    ChatResponseOut,
    CreateKnowledgeDocumentIn,
    KnowledgeIngestOut,
    KnowledgeDownloadOut,
    KnowledgeDocumentOut,
    RetrievalSearchIn,
    RetrievalSearchOut,
)
from app.domains.shared.schemas import ListResponse, paginated_response

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/knowledge-documents", response_model=ListResponse[KnowledgeDocumentOut])
async def list_knowledge_documents(
    context: Annotated[RequestContext, Depends(get_request_context)],
    session: Annotated[AsyncSession, Depends(get_ai_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    service = KnowledgeDocumentService(session)
    items = await service.list_documents(context.organization_id, limit=limit + 1)
    return paginated_response(items, limit=limit, sort="-created_at")


@router.post("/knowledge-documents", response_model=KnowledgeDocumentOut)
async def create_knowledge_document(
    payload: CreateKnowledgeDocumentIn,
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_ai_db_session)],
) -> dict:
    service = KnowledgeDocumentService(session)
    return await service.create_document(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        payload=payload,
    )


@router.post("/knowledge-documents/upload", response_model=KnowledgeDocumentOut)
async def upload_knowledge_document(
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_ai_db_session)],
    title: Annotated[str, Form()],
    source_type: Annotated[str, Form()] = "pdf",
    file: UploadFile = File(...),
) -> dict:
    content = await file.read()
    service = KnowledgeDocumentService(session)
    return await service.upload_document(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        title=title,
        source_type=source_type,
        file_name=file.filename or "knowledge.pdf",
        mime_type=file.content_type or "application/octet-stream",
        content=content,
        storage=get_storage_provider(),
    )


@router.get(
    "/knowledge-documents/{document_id}/download",
    response_model=KnowledgeDownloadOut,
)
async def create_knowledge_document_download(
    document_id: str,
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_ai_db_session)],
) -> dict:
    return await KnowledgeDocumentService(session).create_download_reference(
        organization_id=context.organization_id,
        document_id=document_id,
    )


@router.get("/downloads/content")
async def download_knowledge_document_content(token: str) -> Response:
    _organization_id, storage_key = verify_storage_download_token(token)
    content = await get_storage_provider().get_bytes(storage_key)
    return Response(content=content, media_type="application/octet-stream")


@router.post("/knowledge-documents/{document_id}/ingest", response_model=KnowledgeIngestOut)
async def ingest_knowledge_document(
    document_id: str,
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_ai_db_session)],
) -> dict:
    service = KnowledgeDocumentService(session)
    return await service.ingest_document(
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        document_id=document_id,
    )


@router.post("/chat", response_model=ChatResponseOut)
async def chat(
    payload: ChatRequestIn,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_ai_db_session)],
) -> dict:
    service = GuardedChatbotService(session)
    return await service.answer(
        organization_id=context.organization_id,
        user_id=context.user_id,
        message=payload.message,
    )


@router.post("/retrieval/search", response_model=RetrievalSearchOut)
async def search_knowledge(
    payload: RetrievalSearchIn,
    context: Annotated[
        RequestContext, Depends(require_roles("admin", "employee", "customer"))
    ],
    session: Annotated[AsyncSession, Depends(get_ai_db_session)],
) -> dict:
    service = KnowledgeRetrievalService(session)
    try:
        return await asyncio.wait_for(
            service.search(
                organization_id=context.organization_id,
                query=payload.query,
                limit=payload.limit,
                actor_user_id=context.user_id,
            ),
            timeout=settings.ai_retrieval_timeout_seconds,
        )
    except TimeoutError:
        return {"items": []}


@router.get("/operations", response_model=AiOperationalTelemetryOut)
async def get_ai_operations(
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_ai_db_session)],
) -> dict:
    return await AiOperationalTelemetryService(session).get_summary(
        organization_id=context.organization_id
    )
