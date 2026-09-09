"""Add per-user Telegram bot connections."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023_telegram_connections"
down_revision: Union[str, None] = "dc6505b9954b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("bot_id", sa.BigInteger(), nullable=False),
        sa.Column("bot_username", sa.String(64), nullable=False),
        sa.Column("allowed_username", sa.String(64), nullable=True),
        sa.Column("webhook_secret", sa.String(128), nullable=False),
        sa.Column("webhook_url", sa.String(500), nullable=False),
        sa.Column("last_update_id", sa.BigInteger(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_telegram_connections_user_id"),
        sa.UniqueConstraint("bot_id", name="uq_telegram_connections_bot_id"),
        sa.UniqueConstraint("webhook_secret", name="uq_telegram_connections_secret"),
    )
    op.create_index("ix_telegram_connections_user_id", "telegram_connections", ["user_id"])
    op.create_index("ix_telegram_connections_webhook_secret", "telegram_connections", ["webhook_secret"])


def downgrade() -> None:
    op.drop_table("telegram_connections")
