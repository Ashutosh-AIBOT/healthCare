"""Add daily nutrition and water logs."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "026_nutrition_logs"
down_revision = "025_timed_recurring_todos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nutrition_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("logged_date", sa.Date(), nullable=False),
        sa.Column("entry_type", sa.String(length=20), nullable=False),
        sa.Column("meal_type", sa.String(length=20), nullable=True),
        sa.Column("item_name", sa.String(length=200), nullable=True),
        sa.Column("calories", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("protein_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("carbs_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fat_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("water_ml", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nutrition_logs_user_id", "nutrition_logs", ["user_id"])
    op.create_index("ix_nutrition_logs_logged_date", "nutrition_logs", ["logged_date"])


def downgrade() -> None:
    op.drop_index("ix_nutrition_logs_logged_date", table_name="nutrition_logs")
    op.drop_index("ix_nutrition_logs_user_id", table_name="nutrition_logs")
    op.drop_table("nutrition_logs")
