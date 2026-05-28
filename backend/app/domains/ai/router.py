from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import RequestContext, get_request_context, require_roles
from app.core.database import get_db_session
from app.core.storage import LocalStorageProvider
from app.domains.ai.chat_service import GuardedChatbotService
from app.domains.ai.knowledge_service import KnowledgeDocumentService
from app.domains.ai.retrieval_service import KnowledgeRetrievalService
from app.domains.ai.schemas import (
    ChatRequestIn,
    ChatResponseOut,
    CreateKnowledgeDocumentIn,
    KnowledgeIngestOut,
    KnowledgeDocumentOut,
    RetrievalSearchIn,
    RetrievalSearchOut,
)
from app.domains.shared.schemas import ListResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/knowledge-documents", response_model=ListResponse[KnowledgeDocumentOut])
async def list_knowledge_documents(
    context: Annotated[RequestContext, Depends(get_request_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict:
    service = KnowledgeDocumentService(session)
    return {"items": await service.list_documents(context.organization_id, limit=limit)}


@router.post("/knowledge-documents", response_model=KnowledgeDocumentOut)
async def create_knowledge_document(
    payload: CreateKnowledgeDocumentIn,
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
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
        storage=LocalStorageProvider(),
    )


@router.post("/knowledge-documents/{document_id}/ingest", response_model=KnowledgeIngestOut)
async def ingest_knowledge_document(
    document_id: str,
    context: Annotated[RequestContext, Depends(require_roles("admin"))],
    session: Annotated[AsyncSession, Depends(get_db_session)],
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
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
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict:
    service = KnowledgeRetrievalService(session)
    return await service.search(
        organization_id=context.organization_id,
        query=payload.query,
        limit=payload.limit,
    )
