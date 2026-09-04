"""add revoked_at to consents and is_active index to consent_documents (M19.2)

Revision ID: 032
Revises: 031
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "consents",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_consents_consent_type", "consents", ["consent_type"], unique=False)
    op.create_index(
        "ix_consent_documents_consent_type",
        "consent_documents",
        ["consent_type"],
        unique=False,
    )
    op.add_column(
        "consent_documents",
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("consent_documents", "is_active")
    op.drop_index("ix_consent_documents_consent_type", table_name="consent_documents")
    op.drop_index("ix_consents_consent_type", table_name="consents")
    op.drop_column("consents", "revoked_at")
