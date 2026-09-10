"""Add timed and recurring todo fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "025_timed_recurring_todos"
down_revision = "024_xomni_pending_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("todos", sa.Column("start_minute", sa.Integer(), nullable=True))
    op.add_column("todos", sa.Column("end_minute", sa.Integer(), nullable=True))
    op.add_column("todos", sa.Column("recurrence_rule", sa.String(length=20), nullable=False, server_default="once"))
    op.add_column("todos", sa.Column("recurrence_until", sa.Date(), nullable=True))
    op.add_column("todos", sa.Column("recurrence_days", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("todos", sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_todos_series_id", "todos", ["series_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_todos_series_id", table_name="todos")
    for name in ("series_id", "recurrence_days", "recurrence_until", "recurrence_rule", "end_minute", "start_minute"):
        op.drop_column("todos", name)
