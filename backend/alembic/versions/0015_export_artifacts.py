"""add export artifacts

Revision ID: 0015_export_artifacts
Revises: 0014_claim_corrections
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0015_export_artifacts"
down_revision = "0014_claim_corrections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "export_artifacts",
        sa.Column("artifact_type", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=120), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("file_asset_id", sa.String(length=64), nullable=True),
        sa.Column("requested_by_user_id", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["file_asset_id"], ["file_assets.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["artifact_type", "file_asset_id", "organization_id", "requested_by_user_id", "resource_id", "resource_type", "status"]:
        op.create_index(f"ix_export_artifacts_{column}", "export_artifacts", [column])


def downgrade() -> None:
    for column in ["status", "resource_type", "resource_id", "requested_by_user_id", "organization_id", "file_asset_id", "artifact_type"]:
        op.drop_index(f"ix_export_artifacts_{column}", table_name="export_artifacts")
    op.drop_table("export_artifacts")
