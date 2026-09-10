"""User-confirmed personal context for tailored Xomni suggestions."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "027_user_personal_context"
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
        sa.Column("source", sa.String(length=20), nullable=False, server_default="USER_CONFIRMED"),
        sa.ForeignKeyConstraint(["family_id"], ["families.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_personal_context_user_id", "user_personal_context", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_personal_context_user_id", table_name="user_personal_context")
    op.drop_table("user_personal_context")
