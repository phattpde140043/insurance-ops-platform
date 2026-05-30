"""add claim corrections

Revision ID: 0014_claim_corrections
Revises: 0013_conversation_handoff
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0014_claim_corrections"
down_revision = "0013_conversation_handoff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insurance_claim_corrections",
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("reviewer_user_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("corrected_fields", sa.JSON(), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("approved_by_user_id", sa.String(length=64), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["claim_id"], ["insurance_incident_reports.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["claim_id", "organization_id", "reviewer_user_id", "status"]:
        op.create_index(f"ix_insurance_claim_corrections_{column}", "insurance_claim_corrections", [column])


def downgrade() -> None:
    for column in ["status", "reviewer_user_id", "organization_id", "claim_id"]:
        op.drop_index(f"ix_insurance_claim_corrections_{column}", table_name="insurance_claim_corrections")
    op.drop_table("insurance_claim_corrections")
