"""Add consented user context for personalized retrieval."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "027_rag_personal_context"
down_revision = "026_nutrition_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_personal_context",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("context_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="USER_CONFIRMED"),
        sa.Column("consent_version", sa.String(length=32), nullable=False, server_default="2026-09-01"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_user_personal_context_user_id", "user_personal_context", ["user_id"], unique=True)
    op.create_index("ix_user_personal_context_family_id", "user_personal_context", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_user_personal_context_family_id", table_name="user_personal_context")
    op.drop_index("ix_user_personal_context_user_id", table_name="user_personal_context")
    op.drop_table("user_personal_context")
