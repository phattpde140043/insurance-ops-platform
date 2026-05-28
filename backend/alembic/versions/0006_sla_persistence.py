"""add sla persistence

Revision ID: 0006_sla_persistence
Revises: 0005_conversation_claim_link
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_sla_persistence"
down_revision = "0005_conversation_claim_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sla_rules",
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("threshold_minutes", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sla_rules_organization_id", "sla_rules", ["organization_id"])
    op.create_index("ix_sla_rules_status", "sla_rules", ["status"])
    op.create_index("ix_sla_rules_target_type", "sla_rules", ["target_type"])

    op.create_table(
        "sla_alerts",
        sa.Column("rule_id", sa.String(length=64), nullable=True),
        sa.Column("target_type", sa.String(length=80), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("breached_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["sla_rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sla_alerts_organization_id", "sla_alerts", ["organization_id"])
    op.create_index("ix_sla_alerts_rule_id", "sla_alerts", ["rule_id"])
    op.create_index("ix_sla_alerts_status", "sla_alerts", ["status"])
    op.create_index("ix_sla_alerts_target_id", "sla_alerts", ["target_id"])
    op.create_index("ix_sla_alerts_target_type", "sla_alerts", ["target_type"])


def downgrade() -> None:
    op.drop_index("ix_sla_alerts_target_type", table_name="sla_alerts")
    op.drop_index("ix_sla_alerts_target_id", table_name="sla_alerts")
    op.drop_index("ix_sla_alerts_status", table_name="sla_alerts")
    op.drop_index("ix_sla_alerts_rule_id", table_name="sla_alerts")
    op.drop_index("ix_sla_alerts_organization_id", table_name="sla_alerts")
    op.drop_table("sla_alerts")
    op.drop_index("ix_sla_rules_target_type", table_name="sla_rules")
    op.drop_index("ix_sla_rules_status", table_name="sla_rules")
    op.drop_index("ix_sla_rules_organization_id", table_name="sla_rules")
    op.drop_table("sla_rules")
