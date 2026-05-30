"""add ai rate limit windows

Revision ID: 0012_ai_rate_limit_windows
Revises: 0011_idempotency_records
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0012_ai_rate_limit_windows"
down_revision = "0011_idempotency_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_rate_limit_windows",
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_id", sa.String(length=64), nullable=False),
        sa.Column("capability", sa.String(length=80), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "subject_type", "subject_id", "capability", "window_started_at", name="uq_ai_rate_limit_window"),
    )
    for column in ["capability", "organization_id", "subject_id", "subject_type", "window_started_at"]:
        op.create_index(f"ix_ai_rate_limit_windows_{column}", "ai_rate_limit_windows", [column])


def downgrade() -> None:
    for column in ["window_started_at", "subject_type", "subject_id", "organization_id", "capability"]:
        op.drop_index(f"ix_ai_rate_limit_windows_{column}", table_name="ai_rate_limit_windows")
    op.drop_table("ai_rate_limit_windows")
