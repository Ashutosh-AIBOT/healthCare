"""auth hardening: handle, consents, otp attempts, 2fa, lockout columns, rls bypass

Revision ID: 011
Revises: 010
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("handle", sa.String(length=30), nullable=True))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("failed_login_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("totp_enabled", sa.Boolean(), server_default="false", nullable=False))
    op.create_index("ix_users_handle", "users", ["handle"], unique=True)

    op.add_column("otp_codes", sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False))

    op.create_table(
        "consent_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("consent_type", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("consent_type", "version", name="uq_consent_documents_type_version"),
    )

    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_type", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Index("ix_consents_user_id", "user_id"),
    )

    op.create_table(
        "totp_secrets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("secret_encrypted", sa.String(255), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "backup_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code_hash", sa.String(255), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Index("ix_backup_codes_user_id", "user_id"),
    )

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO system_settings (key, value, updated_at) VALUES
              ('invitation_ttl_days', '14', NOW()),
              ('majority_age_years', '18', NOW()),
              ('otp_max_attempts', '5', NOW()),
              ('otp_max_sends_per_hour', '3', NOW()),
              ('login_max_failures', '10', NOW()),
              ('login_lockout_minutes', '15', NOW())
            """
        )
    )

    # Seed current consent document versions
    op.execute(
        sa.text(
            """
            INSERT INTO consent_documents (id, consent_type, version, title, body_url, created_at, updated_at) VALUES
              (gen_random_uuid(), 'terms', '2026-09-01', 'Terms of Service', '/legal/terms', NOW(), NOW()),
              (gen_random_uuid(), 'privacy', '2026-09-01', 'Privacy Policy', '/legal/privacy', NOW(), NOW()),
              (gen_random_uuid(), 'medical_disclaimer', '2026-09-01', 'Medical Disclaimer', '/legal/medical-disclaimer', NOW(), NOW())
            """
        )
    )

    conn = op.get_bind()
    # Allow auth bootstrap lookups when app.bypass_rls = on
    conn.execute(sa.text("DROP POLICY IF EXISTS users_isolation ON users"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY users_isolation ON users
                FOR ALL
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
    conn.execute(sa.text("DROP POLICY IF EXISTS sessions_isolation ON sessions"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY sessions_isolation ON sessions
                FOR ALL
                USING (
                    current_setting('app.bypass_rls', true) = 'on'
                    OR EXISTS (
                        SELECT 1 FROM users
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

    for table in ("families", "family_members", "invites", "member_medical_profiles", "member_transfers"):
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))

    conn.execute(
        sa.text(
            """
            CREATE POLICY families_isolation ON families FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR id = COALESCE(NULLIF(current_setting('app.family_id', true), '')::uuid,
                                 '00000000-0000-0000-0000-000000000000')
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY family_members_isolation ON family_members FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR family_id = COALESCE(NULLIF(current_setting('app.family_id', true), '')::uuid,
                                        '00000000-0000-0000-0000-000000000000')
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY invites_isolation ON invites FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR family_id = COALESCE(NULLIF(current_setting('app.family_id', true), '')::uuid,
                                        '00000000-0000-0000-0000-000000000000')
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY member_medical_profiles_isolation ON member_medical_profiles FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM family_members fm
                    WHERE fm.id = member_medical_profiles.member_id
                      AND fm.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY member_transfers_isolation ON member_transfers FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR from_family_id = COALESCE(NULLIF(current_setting('app.family_id', true), '')::uuid,
                                             '00000000-0000-0000-0000-000000000000')
                OR to_family_id = COALESCE(NULLIF(current_setting('app.family_id', true), '')::uuid,
                                           '00000000-0000-0000-0000-000000000000')
            )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    for policy, table in (
        ("families_isolation", "families"),
        ("family_members_isolation", "family_members"),
        ("invites_isolation", "invites"),
        ("member_medical_profiles_isolation", "member_medical_profiles"),
        ("member_transfers_isolation", "member_transfers"),
    ):
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {policy} ON {table}"))
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    op.drop_table("backup_codes")
    op.drop_table("totp_secrets")
    op.drop_table("consents")
    op.drop_table("consent_documents")
    op.drop_table("system_settings")
    op.drop_column("otp_codes", "attempt_count")
    op.drop_index("ix_users_handle", table_name="users")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "handle")
