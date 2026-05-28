"""add claim lifecycle persistence

Revision ID: 0003_claim_lifecycle
Revises: 0002_queue_fields
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_claim_lifecycle"
down_revision = "0002_queue_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "insurance_incident_reports",
        sa.Column(
            "claim_state",
            sa.String(length=60),
            nullable=False,
            server_default="reported",
        ),
    )
    op.create_index(
        "ix_insurance_incident_reports_claim_state",
        "insurance_incident_reports",
        ["claim_state"],
        unique=False,
    )

    op.create_table(
        "insurance_claim_transitions",
        sa.Column("claim_id", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.String(length=64), nullable=False),
        sa.Column("from_state", sa.String(length=60), nullable=True),
        sa.Column("to_state", sa.String(length=60), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["claim_id"], ["insurance_incident_reports.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_insurance_claim_transitions_actor_user_id",
        "insurance_claim_transitions",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_insurance_claim_transitions_claim_id",
        "insurance_claim_transitions",
        ["claim_id"],
        unique=False,
    )
    op.create_index(
        "ix_insurance_claim_transitions_from_state",
        "insurance_claim_transitions",
        ["from_state"],
        unique=False,
    )
    op.create_index(
        "ix_insurance_claim_transitions_organization_id",
        "insurance_claim_transitions",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_insurance_claim_transitions_to_state",
        "insurance_claim_transitions",
        ["to_state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_insurance_claim_transitions_to_state",
        table_name="insurance_claim_transitions",
    )
    op.drop_index(
        "ix_insurance_claim_transitions_organization_id",
        table_name="insurance_claim_transitions",
    )
    op.drop_index(
        "ix_insurance_claim_transitions_from_state",
        table_name="insurance_claim_transitions",
    )
    op.drop_index(
        "ix_insurance_claim_transitions_claim_id",
        table_name="insurance_claim_transitions",
    )
    op.drop_index(
        "ix_insurance_claim_transitions_actor_user_id",
        table_name="insurance_claim_transitions",
    )
    op.drop_table("insurance_claim_transitions")
    op.drop_index(
        "ix_insurance_incident_reports_claim_state",
        table_name="insurance_incident_reports",
    )
    op.drop_column("insurance_incident_reports", "claim_state")
