"""create notification tables

Revision ID: 024
Revises: 023
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel_in_app", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("channel_email", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("channel_sms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("channel_push", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("quiet_hours_start", sa.String(length=8), nullable=True),
        sa.Column("quiet_hours_end", sa.String(length=8), nullable=True),
        sa.Column("quiet_hours_timezone", sa.String(length=64), nullable=True),
    )
    op.create_index(op.f("ix_notification_preferences_user_id"), "notification_preferences", ["user_id"], unique=True)

    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"])

    op.create_table(
        "notification_delivery_logs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("notification_id", sa.UUID(as_uuid=True), sa.ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_notification_delivery_logs_notification_id"), "notification_delivery_logs", ["notification_id"])

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE notification_preferences FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY notification_preferences_isolation ON notification_preferences FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR user_id = COALESCE(
                    NULLIF(current_setting('app.current_user_id', true), '')::uuid,
                    '00000000-0000-0000-0000-000000000000'
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE notifications FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY notifications_isolation ON notifications FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR user_id = COALESCE(
                    NULLIF(current_setting('app.current_user_id', true), '')::uuid,
                    '00000000-0000-0000-0000-000000000000'
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE notification_delivery_logs ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE notification_delivery_logs FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY notification_delivery_logs_isolation ON notification_delivery_logs FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM notifications n
                    WHERE n.id = notification_delivery_logs.notification_id
                      AND n.user_id = COALESCE(
                          NULLIF(current_setting('app.current_user_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP POLICY IF EXISTS notification_delivery_logs_isolation ON notification_delivery_logs"))
    conn.execute(sa.text("ALTER TABLE notification_delivery_logs DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS notifications_isolation ON notifications"))
    conn.execute(sa.text("ALTER TABLE notifications DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS notification_preferences_isolation ON notification_preferences"))
    conn.execute(sa.text("ALTER TABLE notification_preferences DISABLE ROW LEVEL SECURITY"))
    op.drop_index(op.f("ix_notification_delivery_logs_notification_id"), table_name="notification_delivery_logs")
    op.drop_table("notification_delivery_logs")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_notification_preferences_user_id"), table_name="notification_preferences")
    op.drop_table("notification_preferences")
