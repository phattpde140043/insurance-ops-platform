"""add file asset checksum

Revision ID: 0008_file_asset_checksum
Revises: 0007_background_job_claiming
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_file_asset_checksum"
down_revision = "0007_background_job_claiming"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "file_assets",
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("file_assets", "checksum_sha256")
