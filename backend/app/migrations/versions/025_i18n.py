"""add locale column to users

Revision ID: 025
Revises: 024
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("locale", sa.String(length=8), server_default="en", nullable=False))
    op.create_index(op.f("ix_users_locale"), "users", ["locale"])


def downgrade() -> None:
    op.drop_index(op.f("ix_users_locale"), table_name="users")
    op.drop_column("users", "locale")
