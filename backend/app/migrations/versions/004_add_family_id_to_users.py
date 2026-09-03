"""add family_id to users

Revision ID: 004
Revises: 003
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_index("ix_users_family_id", "users", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_users_family_id", table_name="users")
    op.drop_column("users", "family_id")
