from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.model_mixins import IdMixin, TenantMixin, TimestampMixin


class InsurancePlan(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_plans"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    premium: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class InsuranceWorkflow(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_workflows"
    __table_args__ = (
        UniqueConstraint("organization_id", "key", name="uq_insurance_workflow_key"),
    )

    key: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)


class InsuranceCustomer(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_customers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(80))
    linked_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)


class InsurancePolicy(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_policies"

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("insurance_customers.id"), index=True, nullable=False
    )
    plan_id: Mapped[str] = mapped_column(
        ForeignKey("insurance_plans.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)


class InsuranceEmployeeAssignment(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_employee_assignments"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "customer_id",
            "employee_user_id",
            name="uq_customer_employee_assignment",
        ),
    )

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("insurance_customers.id"), index=True, nullable=False
    )
    employee_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    due_at: Mapped[str | None] = mapped_column(String(80), index=True)


class InsuranceIncidentReport(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_incident_reports"

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("insurance_customers.id"), index=True, nullable=False
    )
    policy_id: Mapped[str | None] = mapped_column(ForeignKey("insurance_policies.id"))
    incident_type: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    claim_state: Mapped[str] = mapped_column(
        String(60), index=True, default="reported", nullable=False
    )
    priority: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    due_at: Mapped[str | None] = mapped_column(String(80), index=True)


class InsuranceClaimTransition(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_claim_transitions"

    claim_id: Mapped[str] = mapped_column(
        ForeignKey("insurance_incident_reports.id"), index=True, nullable=False
    )
    actor_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    from_state: Mapped[str | None] = mapped_column(String(60), index=True)
    to_state: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class InsuranceAppointment(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_appointments"

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("insurance_customers.id"), index=True, nullable=False
    )
    employee_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    scheduled_at: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    due_at: Mapped[str | None] = mapped_column(String(80), index=True)


class InsuranceConversation(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_conversations"

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("insurance_customers.id"), index=True, nullable=False
    )
    claim_id: Mapped[str | None] = mapped_column(
        ForeignKey("insurance_incident_reports.id"), index=True
    )
    employee_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    due_at: Mapped[str | None] = mapped_column(String(80), index=True)


class InsuranceMessage(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "insurance_messages"

    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("insurance_conversations.id"), index=True, nullable=False
    )
    sender_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(40), default="user", nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    citations_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
