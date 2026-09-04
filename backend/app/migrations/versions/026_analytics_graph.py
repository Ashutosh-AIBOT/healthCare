"""create analytics_events and graph_projections tables with RLS

Revision ID: 026
Revises: 025
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=True),
        sa.Column("family_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("device", sa.String(length=64), nullable=True),
        sa.Column("locale", sa.String(length=8), nullable=True),
        sa.Column("app_version", sa.String(length=32), nullable=True),
        sa.Column("plan_tier", sa.String(length=32), nullable=True),
        sa.Column("properties", sa.JSON(), nullable=True),
    )
    op.create_index(op.f("ix_analytics_events_event_name"), "analytics_events", ["event_name"])
    op.create_index(op.f("ix_analytics_events_user_id"), "analytics_events", ["user_id"])
    op.create_index(op.f("ix_analytics_events_occurred_at"), "analytics_events", ["occurred_at"])
    op.create_index(op.f("ix_analytics_events_family_id"), "analytics_events", ["family_id"])

    op.create_table(
        "graph_projections",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sync_status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_index(op.f("ix_graph_projections_entity_id"), "graph_projections", ["entity_id"])

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE analytics_events FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY analytics_events_append ON analytics_events
            FOR INSERT
            WITH CHECK (
                current_setting('app.bypass_rls', true) = 'on'
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY analytics_events_read ON analytics_events
            FOR SELECT
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR family_id = COALESCE(
                    NULLIF(current_setting('app.family_id', true), '')::uuid,
                    '00000000-0000-0000-0000-000000000000'
                )
                OR user_id = (
                    SELECT id::uuid FROM users
                    WHERE users.role = 'platform_admin'
                    LIMIT 1
                )
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY analytics_events_block_dml ON analytics_events
            FOR UPDATE, DELETE
            USING (false)
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE graph_projections ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE graph_projections FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY graph_projections_read ON graph_projections
            FOR SELECT
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM users
                    WHERE users.id = current_setting('app.current_user_id', true)::uuid
                      AND users.role = 'platform_admin'
                )
            )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP POLICY IF EXISTS graph_projections_read ON graph_projections"))
    conn.execute(sa.text("ALTER TABLE graph_projections DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS analytics_events_block_dml ON analytics_events"))
    conn.execute(sa.text("DROP POLICY IF EXISTS analytics_events_read ON analytics_events"))
    conn.execute(sa.text("DROP POLICY IF EXISTS analytics_events_append ON analytics_events"))
    conn.execute(sa.text("ALTER TABLE analytics_events DISABLE ROW LEVEL SECURITY"))

    op.drop_index(op.f("ix_graph_projections_entity_id"), table_name="graph_projections")
    op.drop_table("graph_projections")
    op.drop_index(op.f("ix_analytics_events_family_id"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_occurred_at"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_user_id"), table_name="analytics_events")
    op.drop_index(op.f("ix_analytics_events_event_name"), table_name="analytics_events")
    op.drop_table("analytics_events")
