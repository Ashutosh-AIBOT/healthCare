"""learn catalog: categories, items, body parts, tests (global read-only)

Revision ID: 018
Revises: 017
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learn_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(40), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("kind IN ('food','test_info')", name="ck_learn_categories_kind"),
    )
    op.create_index("ix_learn_categories_kind_order", "learn_categories", ["kind", "sort_order"])
    op.create_index("ix_learn_categories_slug", "learn_categories", ["slug"])

    op.create_table(
        "learn_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("learn_categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("nutrition", postgresql.JSONB(), nullable=True),
        sa.Column("benefits", postgresql.JSONB(), nullable=True),
        sa.Column("healthy_role", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_learn_items_category_order", "learn_items", ["category_id", "sort_order"])
    op.create_index("ix_learn_items_slug", "learn_items", ["slug"])

    op.create_table(
        "test_body_parts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_index("ix_test_body_parts_order", "test_body_parts", ["order_index"])
    op.create_index("ix_test_body_parts_slug", "test_body_parts", ["slug"])

    op.create_table(
        "body_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("body_part_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_body_parts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("what_it_checks", sa.Text(), nullable=True),
        sa.Column("prep_note", sa.Text(), nullable=True),
        sa.Column("fasting_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_body_tests_part_order", "body_tests", ["body_part_id", "sort_order"])
    op.create_index("ix_body_tests_fasting", "body_tests", ["fasting_required"])


def downgrade() -> None:
    op.drop_index("ix_body_tests_fasting", table_name="body_tests")
    op.drop_index("ix_body_tests_part_order", table_name="body_tests")
    op.drop_table("body_tests")
    op.drop_index("ix_test_body_parts_slug", table_name="test_body_parts")
    op.drop_index("ix_test_body_parts_order", table_name="test_body_parts")
    op.drop_table("test_body_parts")
    op.drop_index("ix_learn_items_slug", table_name="learn_items")
    op.drop_index("ix_learn_items_category_order", table_name="learn_items")
    op.drop_table("learn_items")
    op.drop_index("ix_learn_categories_slug", table_name="learn_categories")
    op.drop_index("ix_learn_categories_kind_order", table_name="learn_categories")
    op.drop_table("learn_categories")
