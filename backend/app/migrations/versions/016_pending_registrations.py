"""pending registrations — no user/family rows until email OTP verified

Revision ID: 016
Revises: 015

NOTE: feat/appointments also introduced a 016 on its branch. When that
branch rebases onto main it must rename its migration to 017.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pending_registrations",
        sa.Column("email", sa.String(255), primary_key=True),
        sa.Column("handle", sa.String(30), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(120), nullable=True),
        sa.Column("terms_version", sa.String(32), nullable=False, server_default="2026-09-01"),
        sa.Column("privacy_version", sa.String(32), nullable=False, server_default="2026-09-01"),
        sa.Column(
            "medical_disclaimer_version", sa.String(32), nullable=False, server_default="2026-09-01"
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_pending_registrations_expires_at", "pending_registrations", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_pending_registrations_expires_at", table_name="pending_registrations")
    op.drop_table("pending_registrations")
