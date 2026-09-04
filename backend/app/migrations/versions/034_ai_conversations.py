"""create ai_conversations + ai_messages tables with user-scoped RLS (Module 11 Tier 1)

Revision ID: 034
Revises: 033
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "034"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tier", sa.String(length=32), server_default=sa.text("'tier1_info'"), nullable=False),
        sa.Column("triage_flag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_ai_conversations_user_created",
        "ai_conversations",
        ["user_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "ai_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tier", sa.String(length=32), server_default=sa.text("'tier1_info'"), nullable=False),
        sa.Column("retrieved_chunk_ids", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_ai_messages_conv_created",
        "ai_messages",
        ["conversation_id", "created_at"],
        unique=False,
    )

    conn = op.get_bind()
    for table in ("ai_conversations", "ai_messages"):
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))

    conn.execute(
        sa.text(
            """
            CREATE POLICY ai_conversations_isolation ON ai_conversations FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM users u
                    WHERE u.id = ai_conversations.user_id
                      AND u.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )

    conn.execute(
        sa.text(
            """
            CREATE POLICY ai_messages_isolation ON ai_messages FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM ai_conversations c
                    JOIN users u ON u.id = c.user_id
                    WHERE c.id = ai_messages.conversation_id
                      AND u.family_id = COALESCE(
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
    conn.execute(sa.text("DROP POLICY IF EXISTS ai_messages_isolation ON ai_messages"))
    conn.execute(sa.text("DROP POLICY IF EXISTS ai_conversations_isolation ON ai_conversations"))
    conn.execute(sa.text("ALTER TABLE ai_messages DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE ai_conversations DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_ai_messages_conv_created", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_conversations_user_created", table_name="ai_conversations")
    op.drop_table("ai_conversations")
