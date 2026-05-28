"""schema backbone

Revision ID: 0001_schema_backbone
Revises:
Create Date: 2026-05-26
"""

from alembic import op

from app.core.database import Base
import app.models  # noqa: F401

revision = "0001_schema_backbone"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

