"""create billing tables: plans, subscriptions, usage_records, payouts with RLS

Revision ID: 027
Revises: 025
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "027"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DO $$ BEGIN
                CREATE TYPE plan_interval AS ENUM ('month', 'year');
            EXCEPTION WHEN duplicate_object THEN NULL; END $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DO $$ BEGIN
                CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'past_due');
            EXCEPTION WHEN duplicate_object THEN NULL; END $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DO $$ BEGIN
                CREATE TYPE payout_status AS ENUM ('pending', 'paid', 'failed');
            EXCEPTION WHEN duplicate_object THEN NULL; END $$;
            """
        )
    )

    op.create_table(
        "plans",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(32), nullable=False),
        sa.Column("price_paise", sa.Integer(), nullable=False),
        sa.Column("interval", sa.Enum("month", "year", name="plan_interval"), nullable=False),
        sa.Column("features", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("quota_limits", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_plans_name"),
    )
    op.create_index("ix_plans_name", "plans", ["name"], unique=False)
    op.create_index("ix_plans_is_active", "plans", ["is_active"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.UUID(as_uuid=True), sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.Enum("active", "cancelled", "past_due", name="subscription_status"), server_default="active", nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"], unique=False)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)
    op.create_unique_constraint("uq_subscriptions_user_active", "subscriptions", ["user_id"], postgresql_where=sa.text("status = 'active'"))

    op.create_table(
        "usage_records",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feature_key", sa.String(64), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_usage_records_user_id", "usage_records", ["user_id"], unique=False)
    op.create_index("ix_usage_records_feature_key", "usage_records", ["feature_key"], unique=False)
    op.create_index("ix_usage_records_period_start", "usage_records", ["period_start"], unique=False)
    op.create_index("ix_usage_records_period_end", "usage_records", ["period_end"], unique=False)

    op.create_table(
        "payouts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_profile_id", sa.UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pending", "paid", "failed", name="payout_status"), server_default="pending", nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_payouts_provider_profile_id", "payouts", ["provider_profile_id"], unique=False)
    op.create_index("ix_payouts_status", "payouts", ["status"], unique=False)

    conn.execute(sa.text("ALTER TABLE plans ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE plans FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY plans_public_read ON plans
                FOR SELECT
                USING (true)
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY plans_no_write ON plans
                FOR INSERT, UPDATE, DELETE
                USING (false)
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE subscriptions FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY subscriptions_isolation ON subscriptions
                FOR ALL
                USING (
                    EXISTS (
                        SELECT 1
                        FROM users
                        WHERE users.id = subscriptions.user_id
                          AND users.family_id = COALESCE(
                              NULLIF(current_setting('app.family_id', true), '')::uuid,
                              '00000000-0000-0000-0000-000000000000'
                          )
                    )
                )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE usage_records ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE usage_records FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY usage_records_isolation ON usage_records
                FOR ALL
                USING (
                    EXISTS (
                        SELECT 1
                        FROM users
                        WHERE users.id = usage_records.user_id
                          AND users.family_id = COALESCE(
                              NULLIF(current_setting('app.family_id', true), '')::uuid,
                              '00000000-0000-0000-0000-000000000000'
                          )
                    )
                )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE payouts ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE payouts FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY payouts_isolation ON payouts
                FOR ALL
                USING (
                    EXISTS (
                        SELECT 1
                        FROM provider_profiles pp
                        JOIN users u ON u.id = pp.user_id
                        WHERE pp.id = payouts.provider_profile_id
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
    conn.execute(sa.text("DROP POLICY IF EXISTS payouts_isolation ON payouts"))
    conn.execute(sa.text("ALTER TABLE payouts DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP TABLE IF EXISTS payouts CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS payout_status"))

    conn.execute(sa.text("DROP POLICY IF EXISTS usage_records_isolation ON usage_records"))
    conn.execute(sa.text("ALTER TABLE usage_records DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP TABLE IF EXISTS usage_records CASCADE"))

    conn.execute(sa.text("DROP POLICY IF EXISTS subscriptions_isolation ON subscriptions"))
    conn.execute(sa.text("ALTER TABLE subscriptions DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP TABLE IF EXISTS subscriptions CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS subscription_status"))

    conn.execute(sa.text("DROP POLICY IF EXISTS plans_no_write ON plans"))
    conn.execute(sa.text("DROP POLICY IF EXISTS plans_public_read ON plans"))
    conn.execute(sa.text("ALTER TABLE plans DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP TABLE IF EXISTS plans CASCADE"))
    conn.execute(sa.text("DROP TYPE IF EXISTS plan_interval"))
