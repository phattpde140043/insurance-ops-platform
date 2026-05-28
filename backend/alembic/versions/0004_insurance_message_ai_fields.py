"""add insurance message ai fields

Revision ID: 0004_insurance_message_ai_fields
Revises: 0003_claim_lifecycle
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_insurance_message_ai_fields"
down_revision = "0003_claim_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "insurance_messages",
        sa.Column(
            "role",
            sa.String(length=40),
            nullable=False,
            server_default="user",
        ),
    )
    op.add_column(
        "insurance_messages",
        sa.Column(
            "citations_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("insurance_messages", "citations_json")
    op.drop_column("insurance_messages", "role")
