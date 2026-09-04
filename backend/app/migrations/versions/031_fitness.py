"""fitness logs and targets with family-scoped RLS

Revision ID: 031
Revises: 028
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "031"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fitness_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("logged_date", sa.Date(), nullable=False),
        sa.Column("activity_type", sa.String(16), nullable=False),
        sa.Column("value", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_fitness_logs_user_date", "fitness_logs", ["user_id", "logged_date"])
    op.create_index(
        "ix_fitness_logs_user_date_type", "fitness_logs", ["user_id", "logged_date", "activity_type"]
    )

    op.create_table(
        "fitness_targets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activity_type", sa.String(16), nullable=False),
        sa.Column("daily_target", sa.Numeric(12, 2), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.UniqueConstraint("user_id", "activity_type", name="uq_fitness_targets_user_type"),
    )
    op.create_index("ix_fitness_targets_user_id", "fitness_targets", ["user_id"])

    conn = op.get_bind()
    for table in ("fitness_logs", "fitness_targets"):
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        conn.execute(
            sa.text(
                f"""
                CREATE POLICY {table}_isolation ON {table} FOR ALL
                USING (
                    current_setting('app.bypass_rls', true) = 'on'
                    OR EXISTS (
                        SELECT 1 FROM users u
                        WHERE u.id = {table}.user_id
                          AND u.family_id IS NOT NULL
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
    for table in ("fitness_logs", "fitness_targets"):
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_isolation ON {table}"))
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    op.drop_index("ix_fitness_targets_user_id", table_name="fitness_targets")
    op.drop_table("fitness_targets")
    op.drop_index("ix_fitness_logs_user_date_type", table_name="fitness_logs")
    op.drop_index("ix_fitness_logs_user_date", table_name="fitness_logs")
    op.drop_table("fitness_logs")
