"""create lab_tests table

Revision ID: 019
Revises: 018
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lab_tests",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("canonical_unit", sa.String(length=64), nullable=True),
        sa.Column("fasting_required", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sample_type", sa.String(length=64), nullable=True),
        sa.Column("turnaround_hours", sa.Integer(), nullable=True),
        sa.Column("price_paise", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.create_index(op.f("ix_lab_tests_slug"), "lab_tests", ["slug"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_lab_tests_slug"), table_name="lab_tests")
    op.drop_table("lab_tests")
