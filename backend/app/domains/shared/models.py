from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.model_mixins import IdMixin, TenantMixin, TimestampMixin


class FileAsset(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "file_assets"

    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class BackgroundJob(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "background_jobs"

    job_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(120), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(120), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    locked_by: Mapped[str | None] = mapped_column(String(120), index=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DomainOutboxEvent(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "domain_outbox_events"

    event_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    producer_module: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    locked_by: Mapped[str | None] = mapped_column(String(120), index=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class IdempotencyRecord(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "actor_user_id",
            "command_name",
            "idempotency_key",
            name="uq_idempotency_command_key",
        ),
    )

    actor_user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    command_name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(120), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), index=True)
    response_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ExportArtifact(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "export_artifacts"

    artifact_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    file_asset_id: Mapped[str | None] = mapped_column(ForeignKey("file_assets.id"), index=True)
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
