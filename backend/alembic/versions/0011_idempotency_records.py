"""add idempotency records

Revision ID: 0011_idempotency_records
Revises: 0010_dashboard_read_models
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_idempotency_records"
down_revision = "0010_dashboard_read_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_records",
        sa.Column("actor_user_id", sa.String(length=64), nullable=False),
        sa.Column("command_name", sa.String(length=120), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("response_metadata", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "actor_user_id", "command_name", "idempotency_key", name="uq_idempotency_command_key"),
    )
    for column in ["actor_user_id", "command_name", "idempotency_key", "organization_id", "resource_id", "resource_type", "status"]:
        op.create_index(f"ix_idempotency_records_{column}", "idempotency_records", [column])


def downgrade() -> None:
    for column in ["status", "resource_type", "resource_id", "organization_id", "idempotency_key", "command_name", "actor_user_id"]:
        op.drop_index(f"ix_idempotency_records_{column}", table_name="idempotency_records")
    op.drop_table("idempotency_records")
