"""add dashboard read models

Revision ID: 0010_dashboard_read_models
Revises: 0009_domain_outbox_events
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_dashboard_read_models"
down_revision = "0009_domain_outbox_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_metric_projections",
        sa.Column("metric_key", sa.String(length=120), nullable=False),
        sa.Column("dimension", sa.String(length=120), nullable=False),
        sa.Column("time_bucket", sa.String(length=40), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "metric_key", "dimension", "time_bucket", name="uq_dashboard_metric_projection"),
    )
    op.create_table(
        "dashboard_sla_target_projections",
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("due_at", sa.String(length=80), nullable=True),
        sa.Column("last_event_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "target_type", "target_id", name="uq_dashboard_sla_target_projection"),
    )
    op.create_table(
        "dashboard_projection_events",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "event_id", name="uq_dashboard_projection_event"),
    )
    for table_name, columns in {
        "dashboard_metric_projections": ["dimension", "metric_key", "organization_id", "time_bucket"],
        "dashboard_sla_target_projections": ["due_at", "last_event_id", "organization_id", "status", "target_id", "target_type"],
        "dashboard_projection_events": ["event_id", "event_type", "organization_id"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table_name}_{column}", table_name, [column])


def downgrade() -> None:
    for table_name, columns in {
        "dashboard_projection_events": ["organization_id", "event_type", "event_id"],
        "dashboard_sla_target_projections": ["target_type", "target_id", "status", "organization_id", "last_event_id", "due_at"],
        "dashboard_metric_projections": ["time_bucket", "organization_id", "metric_key", "dimension"],
    }.items():
        for column in columns:
            op.drop_index(f"ix_{table_name}_{column}", table_name=table_name)
        op.drop_table(table_name)
