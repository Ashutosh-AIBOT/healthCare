"""create consent_grants table

Revision ID: 016
Revises: 015
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            CREATE TYPE consent_scope AS ENUM (
                'lab_reports',
                'prescriptions',
                'vitals',
                'medical_profile',
                'nutrition',
                'all'
            )
            """
        )
    )

    op.create_table(
        "consent_grants",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("family_id", sa.UUID(as_uuid=True), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("grantor_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("grantee_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scope", sa.Enum("lab_reports", "prescriptions", "vitals", "medical_profile", "nutrition", "all", name="consent_scope"), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_consent_grants_family_id"), "consent_grants", ["family_id"])
    op.create_index(op.f("ix_consent_grants_grantee_user_id"), "consent_grants", ["grantee_user_id"])
    op.create_index(op.f("ix_consent_grants_member_id"), "consent_grants", ["member_id"])
    op.create_index("ix_consent_grants_family_member_scope", "consent_grants", ["family_id", "member_id", "scope"])

    conn.execute(sa.text("ALTER TABLE consent_grants ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE consent_grants FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY consent_grants_isolation ON consent_grants FOR ALL
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
    conn.execute(sa.text("DROP POLICY IF EXISTS consent_grants_isolation ON consent_grants"))
    conn.execute(sa.text("ALTER TABLE consent_grants DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_consent_grants_family_member_scope", table_name="consent_grants")
    op.drop_index(op.f("ix_consent_grants_member_id"), table_name="consent_grants")
    op.drop_index(op.f("ix_consent_grants_grantee_user_id"), table_name="consent_grants")
    op.drop_index(op.f("ix_consent_grants_family_id"), table_name="consent_grants")
    op.drop_table("consent_grants")
    conn.execute(sa.text("DROP TYPE IF EXISTS consent_scope"))
