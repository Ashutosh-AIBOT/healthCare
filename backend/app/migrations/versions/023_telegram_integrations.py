"""telegram integrations: per-user bot token + link codes + chat binding

Revision ID: 023
Revises: dc6505b9954b
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "023"
down_revision: Union[str, None] = "dc6505b9954b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("bot_token_encrypted", sa.Text(), nullable=False),
        sa.Column("bot_username", sa.String(64), nullable=True),
        sa.Column("allowed_username", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("telegram_chat_id", sa.String(64), nullable=True, unique=True),
        sa.Column("link_code_hash", sa.String(64), nullable=True),
        sa.Column("link_code_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_telegram_integrations_user", "telegram_integrations", ["user_id"])
    op.create_index("ix_telegram_integrations_chat", "telegram_integrations", ["telegram_chat_id"])

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE telegram_integrations ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE telegram_integrations FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY telegram_integrations_isolation ON telegram_integrations FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR user_id IN (
                    SELECT id FROM users WHERE family_id = COALESCE(
                        NULLIF(current_setting('app.family_id', true), '')::uuid,
                        '00000000-0000-0000-0000-000000000000'
                    )
                )
            )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP POLICY IF EXISTS telegram_integrations_isolation ON telegram_integrations"))
    conn.execute(sa.text("ALTER TABLE telegram_integrations DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_telegram_integrations_chat", table_name="telegram_integrations")
    op.drop_index("ix_telegram_integrations_user", table_name="telegram_integrations")
    op.drop_table("telegram_integrations")
