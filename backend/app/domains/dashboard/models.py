from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.model_mixins import IdMixin, TenantMixin, TimestampMixin


class SlaRule(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "sla_rules"

    target_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    threshold_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    severity: Mapped[str] = mapped_column(String(40), default="warning", nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)


class SlaAlert(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "sla_alerts"

    rule_id: Mapped[str | None] = mapped_column(ForeignKey("sla_rules.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    breached_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DashboardMetricProjection(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "dashboard_metric_projections"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "metric_key",
            "dimension",
            "time_bucket",
            name="uq_dashboard_metric_projection",
        ),
    )

    metric_key: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    dimension: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    time_bucket: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class DashboardSlaTargetProjection(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "dashboard_sla_target_projections"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "target_type",
            "target_id",
            name="uq_dashboard_sla_target_projection",
        ),
    )

    target_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    due_at: Mapped[str | None] = mapped_column(String(80), index=True)
    last_event_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)


class DashboardProjectionEvent(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "dashboard_projection_events"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "event_id",
            name="uq_dashboard_projection_event",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
