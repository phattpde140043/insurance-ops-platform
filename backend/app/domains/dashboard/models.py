from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
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
