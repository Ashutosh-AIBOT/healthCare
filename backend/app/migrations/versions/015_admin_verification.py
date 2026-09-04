"""admin verification endpoints: provider verification audit log and user suspension fields

Revision ID: 015
Revises: 014
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_verification_audit_logs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "provider_profile_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("previous_status", sa.String(32), nullable=True),
        sa.Column("new_status", sa.String(32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_provider_verification_audit_logs_profile",
        "provider_verification_audit_logs",
        ["provider_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_provider_verification_audit_logs_actor",
        "provider_verification_audit_logs",
        ["actor_user_id"],
        unique=False,
    )

    op.add_column(
        "users",
        sa.Column("is_suspended", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "suspended_by_user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("suspended_reason", sa.Text(), nullable=True),
    )

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE provider_verification_audit_logs ENABLE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            "CREATE POLICY provider_verification_audit_logs_isolation "
            "ON provider_verification_audit_logs FOR ALL "
            "USING (current_setting(\'app.bypass_rls\', true) = \'on\')"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP POLICY IF EXISTS provider_verification_audit_logs_isolation ON provider_verification_audit_logs"))
    conn.execute(sa.text("ALTER TABLE provider_verification_audit_logs DISABLE ROW LEVEL SECURITY"))

    op.drop_column("users", "suspended_reason")
    op.drop_column("users", "suspended_by_user_id")
    op.drop_column("users", "suspended_at")
    op.drop_column("users", "is_suspended")

    op.drop_index(
        "ix_provider_verification_audit_logs_actor",
        table_name="provider_verification_audit_logs",
    )
    op.drop_index(
        "ix_provider_verification_audit_logs_profile",
        table_name="provider_verification_audit_logs",
    )
    op.drop_table("provider_verification_audit_logs")
