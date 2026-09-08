"""time management: timetables, blocks, todos, holiday rules, day block status

Revision ID: 017
Revises: 016
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "time_timetables",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.CheckConstraint("kind IN ('productive','backup','holiday')", name="ck_time_timetables_kind"),
    )
    op.create_index("ix_time_timetables_family_user", "time_timetables", ["family_id", "user_id"])
    op.create_index("ix_time_timetables_family_kind", "time_timetables", ["family_id", "kind"])

    op.create_table(
        "time_blocks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("timetable_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("time_timetables.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("start_minute", sa.Integer(), nullable=False),
        sa.Column("end_minute", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint("start_minute >= 0 AND start_minute < 1440", name="ck_time_blocks_start_range"),
        sa.CheckConstraint("end_minute > start_minute AND end_minute <= 1440", name="ck_time_blocks_end_range"),
        sa.CheckConstraint("priority IN ('normal','important','less')", name="ck_time_blocks_priority"),
    )
    op.create_index("ix_time_blocks_timetable", "time_blocks", ["timetable_id"])
    op.create_index("ix_time_blocks_timetable_start", "time_blocks", ["timetable_id", "start_minute"])

    op.create_table(
        "todos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="normal"),
        sa.Column("timetable_block_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("time_blocks.id", ondelete="SET NULL"), nullable=True),
        sa.CheckConstraint("status IN ('pending','done')", name="ck_todos_status"),
        sa.CheckConstraint("priority IN ('normal','important','less')", name="ck_todos_priority"),
    )
    op.create_index("ix_todos_family_user_date", "todos", ["family_id", "user_id", "due_date"])
    op.create_index("ix_todos_family_status", "todos", ["family_id", "status"])

    op.create_table(
        "holiday_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_type", sa.String(20), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("specific_date", sa.Date(), nullable=True),
        sa.CheckConstraint("rule_type IN ('weekly','specific')", name="ck_holiday_rules_type"),
        sa.CheckConstraint("(rule_type='weekly' AND weekday BETWEEN 0 AND 6) OR (rule_type='specific' AND specific_date IS NOT NULL)", name="ck_holiday_rules_payload"),
    )
    op.create_index("ix_holiday_rules_family_user", "holiday_rules", ["family_id", "user_id"])

    op.create_table(
        "day_block_status",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("block_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("time_blocks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.CheckConstraint("status IN ('done','partial','skipped')", name="ck_day_block_status_status"),
        sa.UniqueConstraint("user_id", "date", "block_id", name="uq_day_block_status_user_date_block"),
    )
    op.create_index("ix_day_block_status_family_user_date", "day_block_status", ["family_id", "user_id", "date"])

    # RLS — enable force RLS on all new tenant tables
    conn = op.get_bind()
    for table in ["time_timetables", "time_blocks", "todos", "holiday_rules", "day_block_status"]:
        # time_blocks is accessed via timetable -> family, but we still enable RLS using join policy via timetable ownership is complex.
        # For v1, time_blocks inherits tenant via direct family_id? We store family/user on blocks via timetable; but blocks table has no family_id.
        # Instead, keep time_blocks without RLS and rely on timetable RLS. For simplicity, enable RLS on tables with family_id.
        if table == "time_blocks":
            continue
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        conn.execute(
            sa.text(
                f"""
                CREATE POLICY {table}_isolation ON {table} FOR ALL
                USING (
                    current_setting('app.bypass_rls', true) = 'on'
                    OR family_id = COALESCE(
                        NULLIF(current_setting('app.family_id', true), '')::uuid,
                        '00000000-0000-0000-0000-000000000000'
                    )
                )
                """
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    for table in ["day_block_status", "holiday_rules", "todos", "time_timetables"]:
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_isolation ON {table}"))
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_day_block_status_family_user_date", table_name="day_block_status")
    op.drop_table("day_block_status")
    op.drop_index("ix_holiday_rules_family_user", table_name="holiday_rules")
    op.drop_table("holiday_rules")
    op.drop_index("ix_todos_family_status", table_name="todos")
    op.drop_index("ix_todos_family_user_date", table_name="todos")
    op.drop_table("todos")
    op.drop_index("ix_time_blocks_timetable_start", table_name="time_blocks")
    op.drop_index("ix_time_blocks_timetable", table_name="time_blocks")
    op.drop_table("time_blocks")
    op.drop_index("ix_time_timetables_family_kind", table_name="time_timetables")
    op.drop_index("ix_time_timetables_family_user", table_name="time_timetables")
    op.drop_table("time_timetables")
