"""telegram check-ins: interval setting, dedup, morning slots

Revision ID: 024
Revises: 023
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "telegram_integrations",
        sa.Column("checkin_hours", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "telegram_integrations",
        sa.Column("last_checkin_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "telegram_integrations",
        sa.Column("day_start_hour", sa.Integer(), nullable=False, server_default="6"),
    )
    op.add_column(
        "telegram_integrations",
        sa.Column("day_end_hour", sa.Integer(), nullable=False, server_default="22"),
    )

    op.create_table(
        "telegram_updates",
        sa.Column("update_id", sa.BigInteger(), primary_key=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "telegram_checkin_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("slot_time", sa.String(5), nullable=False),
        sa.Column("timetable_block_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("time_blocks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.CheckConstraint("status IN ('pending','sent','answered','skipped','expired')", name="ck_checkin_slots_status"),
        sa.UniqueConstraint("user_id", "date", "slot_time", name="uq_checkin_slots_user_date_time"),
    )
    op.create_index("ix_checkin_slots_user_date", "telegram_checkin_slots", ["user_id", "date"])
    op.create_index("ix_checkin_slots_status", "telegram_checkin_slots", ["status"])

    conn = op.get_bind()
    for table in ["telegram_updates", "telegram_checkin_slots"]:
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY telegram_updates_isolation ON telegram_updates FOR ALL
            USING (current_setting('app.bypass_rls', true) = 'on')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY telegram_checkin_slots_isolation ON telegram_checkin_slots FOR ALL
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
    conn.execute(sa.text("DROP POLICY IF EXISTS telegram_checkin_slots_isolation ON telegram_checkin_slots"))
    conn.execute(sa.text("DROP POLICY IF EXISTS telegram_updates_isolation ON telegram_updates"))
    conn.execute(sa.text("ALTER TABLE telegram_checkin_slots DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE telegram_updates DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_checkin_slots_status", table_name="telegram_checkin_slots")
    op.drop_index("ix_checkin_slots_user_date", table_name="telegram_checkin_slots")
    op.drop_table("telegram_checkin_slots")
    op.drop_table("telegram_updates")
    op.drop_column("telegram_integrations", "day_end_hour")
    op.drop_column("telegram_integrations", "day_start_hour")
    op.drop_column("telegram_integrations", "last_checkin_at")
    op.drop_column("telegram_integrations", "checkin_hours")
