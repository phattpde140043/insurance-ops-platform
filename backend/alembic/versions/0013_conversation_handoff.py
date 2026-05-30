"""add conversation handoff fields

Revision ID: 0013_conversation_handoff
Revises: 0012_ai_rate_limit_windows
Create Date: 2026-05-31
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_conversation_handoff"
down_revision = "0012_ai_rate_limit_windows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "insurance_conversations",
        sa.Column("needs_human", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "insurance_conversations",
        sa.Column("handoff_reason", sa.String(length=80), nullable=True),
    )
    op.create_index(
        "ix_insurance_conversations_handoff_reason",
        "insurance_conversations",
        ["handoff_reason"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_insurance_conversations_handoff_reason",
        table_name="insurance_conversations",
    )
    op.drop_column("insurance_conversations", "handoff_reason")
    op.drop_column("insurance_conversations", "needs_human")
