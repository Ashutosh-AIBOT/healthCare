"""create user_scores table with family-scoped RLS (Module 4 Dashboard)

Revision ID: 029
Revises: 028
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("composite_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("time_management_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("diet_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column("fitness_score", sa.Float(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "widget_visibility",
            postgresql.JSONB(),
            server_default=sa.text(
                "'{\"time_management\": true, \"diet\": true, \"fitness\": true, \"doctor\": true, \"agency\": false}'::jsonb"
            ),
            nullable=False,
        ),
        sa.Column("chatbot_toggle_state", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_recomputed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_user_scores_user_id", "user_scores", ["user_id"], unique=False)

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE user_scores ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE user_scores FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY user_scores_isolation ON user_scores FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM users u
                    WHERE u.id = user_scores.user_id
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
    conn.execute(sa.text("DROP POLICY IF EXISTS user_scores_isolation ON user_scores"))
    conn.execute(sa.text("ALTER TABLE user_scores DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_user_scores_user_id", table_name="user_scores")
    op.drop_table("user_scores")
