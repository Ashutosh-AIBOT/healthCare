"""enable rls on sessions and users

Revision ID: 005
Revises: 004
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE users ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE users FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY users_isolation ON users
                FOR ALL
                USING (
                    family_id = COALESCE(
                        NULLIF(current_setting('app.family_id', true), '')::uuid,
                        '00000000-0000-0000-0000-000000000000'
                    )
                )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE sessions ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE sessions FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY sessions_isolation ON sessions
                FOR ALL
                USING (
                    EXISTS (
                        SELECT 1
                        FROM users
                        WHERE users.id = sessions.user_id
                          AND users.family_id = COALESCE(
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
    conn.execute(sa.text("DROP POLICY IF EXISTS users_isolation ON users"))
    conn.execute(sa.text("ALTER TABLE users DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS sessions_isolation ON sessions"))
    conn.execute(sa.text("ALTER TABLE sessions DISABLE ROW LEVEL SECURITY"))
