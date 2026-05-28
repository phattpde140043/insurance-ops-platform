"""add conversation claim link

Revision ID: 0005_conversation_claim_link
Revises: 0004_insurance_message_ai_fields
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_conversation_claim_link"
down_revision = "0004_insurance_message_ai_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "insurance_conversations",
        sa.Column("claim_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_insurance_conversations_claim_id",
        "insurance_conversations",
        ["claim_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_insurance_conversations_claim_id",
        "insurance_conversations",
        "insurance_incident_reports",
        ["claim_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_insurance_conversations_claim_id",
        "insurance_conversations",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_insurance_conversations_claim_id",
        table_name="insurance_conversations",
    )
    op.drop_column("insurance_conversations", "claim_id")
