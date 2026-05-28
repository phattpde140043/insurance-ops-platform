"""add workload queue fields

Revision ID: 0002_queue_fields
Revises: 0001_schema_backbone
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_queue_fields"
down_revision = "0001_schema_backbone"
branch_labels = None
depends_on = None

QUEUE_TABLES = (
    "insurance_employee_assignments",
    "insurance_incident_reports",
    "insurance_appointments",
    "insurance_conversations",
)


def upgrade() -> None:
    for table_name in QUEUE_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "priority",
                sa.String(length=40),
                nullable=False,
                server_default="normal",
            ),
        )
        op.add_column(
            table_name,
            sa.Column("due_at", sa.String(length=80), nullable=True),
        )
        op.create_index(
            f"ix_{table_name}_due_at",
            table_name,
            ["due_at"],
            unique=False,
        )


def downgrade() -> None:
    for table_name in reversed(QUEUE_TABLES):
        op.drop_index(f"ix_{table_name}_due_at", table_name=table_name)
        op.drop_column(table_name, "due_at")
        op.drop_column(table_name, "priority")
