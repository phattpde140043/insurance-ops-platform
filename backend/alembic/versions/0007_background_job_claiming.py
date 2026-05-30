"""add durable background job claiming

Revision ID: 0007_background_job_claiming
Revises: 0006_sla_persistence
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_background_job_claiming"
down_revision = "0006_sla_persistence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "background_jobs",
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "background_jobs",
        sa.Column("locked_by", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "background_jobs",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "background_jobs",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "background_jobs",
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_background_jobs_locked_by", "background_jobs", ["locked_by"]
    )
    op.create_index(
        "ix_background_jobs_claimable",
        "background_jobs",
        ["status", "available_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_background_jobs_claimable", table_name="background_jobs")
    op.drop_index("ix_background_jobs_locked_by", table_name="background_jobs")
    op.drop_column("background_jobs", "finished_at")
    op.drop_column("background_jobs", "started_at")
    op.drop_column("background_jobs", "locked_until")
    op.drop_column("background_jobs", "locked_by")
    op.drop_column("background_jobs", "available_at")
