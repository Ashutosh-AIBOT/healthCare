"""Module 10: messaging, conversations, invitations, notifications.

Revision ID: 035
Revises: 032

Notes on RLS:
- Conversations, messages and notifications are *user-scoped*, not family-scoped.
- We use the dedicated `app.user_id` GUC (set per-transaction) for these tables
  so we do not break the existing family-scoped RLS contract.
- `app.bypass_rls` is honoured on every policy for admin/service paths.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "035"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="direct"),
        sa.CheckConstraint(
            "type IN ('family','relationship','doctor','agency','direct')",
            name="ck_conversations_type",
        ),
    )

    op.create_table(
        "conversation_participants",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("conversation_id", "user_id", name="uq_conv_participant_user"),
    )
    op.create_index("ix_conversation_participants_conversation_id", "conversation_participants", ["conversation_id"])
    op.create_index("ix_conversation_participants_user_id", "conversation_participants", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("conversation_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tier", sa.String(length=32), nullable=False, server_default="direct"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "tier IN ('family','relationship','doctor','agency','direct')",
            name="ck_messages_tier",
        ),
    )
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])
    op.create_index("ix_messages_sender_user_id", "messages", ["sender_user_id"])
    op.create_index("ix_messages_created_at", "messages", ["created_at"])

    op.create_table(
        "invitations_v2",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("from_user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("to_user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("to_email", sa.String(length=255), nullable=True),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="family"),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["from_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "type IN ('family','doctor','agency')",
            name="ck_invitations_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending','accepted','declined','expired')",
            name="ck_invitations_status",
        ),
        sa.CheckConstraint(
            "to_user_id IS NOT NULL OR to_email IS NOT NULL",
            name="ck_invitations_target_present",
        ),
    )
    op.create_index("ix_invitations_v2_from_user_id", "invitations_v2", ["from_user_id"])
    op.create_index("ix_invitations_v2_to_user_id", "invitations_v2", ["to_user_id"])
    op.create_index("ix_invitations_v2_status", "invitations_v2", ["status"])
    op.create_index("ix_invitations_v2_expires_at", "invitations_v2", ["expires_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="system"),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "type IN ('message','invitation','system')",
            name="ck_notifications_type",
        ),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    conn = op.get_bind()

    for table in ("conversations", "conversation_participants", "messages", "invitations_v2", "notifications"):
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))

    conn.execute(
        sa.text(
            "CREATE POLICY conversations_isolation ON conversations FOR ALL "
            "USING ("
            "  current_setting('app.bypass_rls', true) = 'on' "
            "  OR EXISTS ("
            "    SELECT 1 FROM conversation_participants p "
            "    WHERE p.conversation_id = conversations.id "
            "      AND p.user_id = COALESCE("
            "        NULLIF(current_setting('app.user_id', true), '')::uuid,"
            "        '00000000-0000-0000-0000-000000000000'"
            "      )"
            "  )"
            ")"
        )
    )

    conn.execute(
        sa.text(
            "CREATE POLICY conversation_participants_isolation ON conversation_participants FOR ALL "
            "USING ("
            "  user_id = COALESCE("
            "    NULLIF(current_setting('app.user_id', true), '')::uuid,"
            "    '00000000-0000-0000-0000-000000000000'"
            "  )"
            "  OR current_setting('app.bypass_rls', true) = 'on'"
            ")"
        )
    )

    conn.execute(
        sa.text(
            "CREATE POLICY messages_isolation ON messages FOR ALL "
            "USING ("
            "  current_setting('app.bypass_rls', true) = 'on' "
            "  OR EXISTS ("
            "    SELECT 1 FROM conversation_participants p "
            "    WHERE p.conversation_id = messages.conversation_id "
            "      AND p.user_id = COALESCE("
            "        NULLIF(current_setting('app.user_id', true), '')::uuid,"
            "        '00000000-0000-0000-0000-000000000000'"
            "      )"
            "  )"
            ")"
        )
    )

    conn.execute(
        sa.text(
            "CREATE POLICY invitations_v2_isolation ON invitations_v2 FOR ALL "
            "USING ("
            "  from_user_id = COALESCE("
            "    NULLIF(current_setting('app.user_id', true), '')::uuid,"
            "    '00000000-0000-0000-0000-000000000000'"
            "  )"
            "  OR to_user_id = COALESCE("
            "    NULLIF(current_setting('app.user_id', true), '')::uuid,"
            "    '00000000-0000-0000-0000-000000000000'"
            "  )"
            "  OR current_setting('app.bypass_rls', true) = 'on'"
            ")"
        )
    )

    conn.execute(
        sa.text(
            "CREATE POLICY notifications_isolation ON notifications FOR ALL "
            "USING ("
            "  user_id = COALESCE("
            "    NULLIF(current_setting('app.user_id', true), '')::uuid,"
            "    '00000000-0000-0000-0000-000000000000'"
            "  )"
            "  OR current_setting('app.bypass_rls', true) = 'on'"
            ")"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    for tbl in (
        "notifications",
        "invitations_v2",
        "messages",
        "conversation_participants",
        "conversations",
    ):
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {tbl}_isolation ON {tbl}"))
        conn.execute(sa.text(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY"))

    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_invitations_v2_expires_at", table_name="invitations_v2")
    op.drop_index("ix_invitations_v2_status", table_name="invitations_v2")
    op.drop_index("ix_invitations_v2_to_user_id", table_name="invitations_v2")
    op.drop_index("ix_invitations_v2_from_user_id", table_name="invitations_v2")
    op.drop_table("invitations_v2")

    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_index("ix_messages_sender_user_id", table_name="messages")
    op.drop_index("ix_messages_conversation_created", table_name="messages")
    op.drop_table("messages")

    op.drop_index("ix_conversation_participants_user_id", table_name="conversation_participants")
    op.drop_index("ix_conversation_participants_conversation_id", table_name="conversation_participants")
    op.drop_table("conversation_participants")

    op.drop_table("conversations")
