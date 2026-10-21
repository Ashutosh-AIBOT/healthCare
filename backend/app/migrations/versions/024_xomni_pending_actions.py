"""persist Xomni proposals until the user confirms or rejects them"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "024_xomni_pending_actions"
down_revision: Union[str, None] = "023_telegram_connections"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("xomni_conversations", sa.Column("pending_action", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("xomni_conversations", sa.Column("pending_action_expires_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("xomni_conversations", "pending_action_expires_at")
    op.drop_column("xomni_conversations", "pending_action")
