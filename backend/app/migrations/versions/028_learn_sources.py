"""Add provenance records for imported Learn content."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028_learn_sources"
down_revision: Union[str, None] = "027_rag_personal_context"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learn_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("license", sa.String(160), nullable=True),
        sa.Column("version", sa.String(80), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True, unique=True),
    )
    op.add_column("learn_items", sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("body_tests", sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_learn_items_source", "learn_items", "learn_sources", ["source_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_body_tests_source", "body_tests", "learn_sources", ["source_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_learn_items_source_id", "learn_items", ["source_id"])
    op.create_index("ix_body_tests_source_id", "body_tests", ["source_id"])


def downgrade() -> None:
    op.drop_index("ix_body_tests_source_id", table_name="body_tests")
    op.drop_index("ix_learn_items_source_id", table_name="learn_items")
    op.drop_constraint("fk_body_tests_source", "body_tests", type_="foreignkey")
    op.drop_constraint("fk_learn_items_source", "learn_items", type_="foreignkey")
    op.drop_column("body_tests", "source_id")
    op.drop_column("learn_items", "source_id")
    op.drop_table("learn_sources")
