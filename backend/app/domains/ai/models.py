from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.model_mixins import IdMixin, TenantMixin, TimestampMixin


class AiProviderCall(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "ai_provider_calls"

    provider: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    capability: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    cost_units: Mapped[int | None] = mapped_column(Integer)
    request_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class KnowledgeBase(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_bases"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)


class KnowledgeDocument(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    knowledge_base_id: Mapped[str | None] = mapped_column(ForeignKey("knowledge_bases.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_asset_id: Mapped[str | None] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)


class KnowledgeChunk(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_chunks"

    document_id: Mapped[str] = mapped_column(
        ForeignKey("knowledge_documents.id"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_ref: Mapped[str | None] = mapped_column(String(255))


class ChatSession(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)


class ChatMessage(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"

    session_id: Mapped[str | None] = mapped_column(ForeignKey("chat_sessions.id"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

