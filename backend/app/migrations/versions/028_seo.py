"""create seo_pages and provider_seo_pages tables with RLS

Revision ID: 028
Revises: 025
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "028"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    op.create_table(
        "seo_pages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("route", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.String(500), nullable=True),
        sa.Column("robots_noindex", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("robots_nofollow", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("quality_gate_passed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("route", name="uq_seo_pages_route"),
    )
    op.create_index("ix_seo_pages_route", "seo_pages", ["route"], unique=False)

    op.create_table(
        "provider_seo_pages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_profile_id", UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("route", sa.String(255), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("is_indexable", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("crawl_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_provider_seo_pages_profile_id", "provider_seo_pages", ["provider_profile_id"], unique=False)
    op.create_index("ix_provider_seo_pages_route", "provider_seo_pages", ["route"], unique=False)

    conn.execute(sa.text("ALTER TABLE seo_pages ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE provider_seo_pages ENABLE ROW LEVEL SECURITY"))

    conn.execute(
        sa.text(
            """
            CREATE POLICY seo_pages_public_read ON seo_pages
                FOR SELECT
                USING (true)
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY seo_pages_admin_write ON seo_pages
                FOR ALL
                USING (current_setting('app.bypass_rls', true) = 'on')
            """
        )
    )

    conn.execute(
        sa.text(
            """
            CREATE POLICY provider_seo_pages_admin_read ON provider_seo_pages
                FOR SELECT
                USING (current_setting('app.bypass_rls', true) = 'on')
            """
        )
    )
    conn.execute(
        sa.text(
            """
            CREATE POLICY provider_seo_pages_admin_write ON provider_seo_pages
                FOR ALL
                USING (current_setting('app.bypass_rls', true) = 'on')
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP POLICY IF EXISTS seo_pages_public_read ON seo_pages"))
    conn.execute(sa.text("DROP POLICY IF EXISTS seo_pages_admin_write ON seo_pages"))
    conn.execute(sa.text("DROP POLICY IF EXISTS provider_seo_pages_admin_read ON provider_seo_pages"))
    conn.execute(sa.text("DROP POLICY IF EXISTS provider_seo_pages_admin_write ON provider_seo_pages"))
    conn.execute(sa.text("ALTER TABLE provider_seo_pages DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE seo_pages DISABLE ROW LEVEL SECURITY"))
    op.drop_index("ix_provider_seo_pages_route", table_name="provider_seo_pages")
    op.drop_index("ix_provider_seo_pages_profile_id", table_name="provider_seo_pages")
    op.drop_table("provider_seo_pages")
    op.drop_index("ix_seo_pages_route", table_name="seo_pages")
    op.drop_table("seo_pages")
