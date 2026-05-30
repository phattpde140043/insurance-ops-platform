"""add domain outbox events

Revision ID: 0009_domain_outbox_events
Revises: 0008_file_asset_checksum
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_domain_outbox_events"
down_revision = "0008_file_asset_checksum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "domain_outbox_events",
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("aggregate_type", sa.String(length=120), nullable=False),
        sa.Column("aggregate_id", sa.String(length=120), nullable=False),
        sa.Column("producer_module", sa.String(length=80), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_domain_outbox_events_claimable", "domain_outbox_events", ["status", "available_at"])
    for column in ["aggregate_id", "aggregate_type", "event_type", "idempotency_key", "locked_by", "organization_id", "producer_module", "status"]:
        op.create_index(f"ix_domain_outbox_events_{column}", "domain_outbox_events", [column])


def downgrade() -> None:
    for column in ["status", "producer_module", "organization_id", "locked_by", "idempotency_key", "event_type", "aggregate_type", "aggregate_id"]:
        op.drop_index(f"ix_domain_outbox_events_{column}", table_name="domain_outbox_events")
    op.drop_index("ix_domain_outbox_events_claimable", table_name="domain_outbox_events")
    op.drop_table("domain_outbox_events")
