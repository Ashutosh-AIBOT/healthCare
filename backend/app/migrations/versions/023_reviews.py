"""create reviews, review_replies and review_flags tables

Revision ID: 023
Revises: 022
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("provider_profile_id", sa.UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("appointment_id", sa.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("member_id", sa.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("is_anonymous", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("moderation_reason", sa.Text(), nullable=True),
        sa.Column("moderated_by_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_reviews_provider_profile_id"), "reviews", ["provider_profile_id"])
    op.create_index(op.f("ix_reviews_member_id"), "reviews", ["member_id"])
    op.create_index(op.f("ix_reviews_author_user_id"), "reviews", ["author_user_id"])
    op.create_index("ix_reviews_provider_status", "reviews", ["provider_profile_id", "status"])

    op.create_table(
        "review_replies",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("review_id", sa.UUID(as_uuid=True), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="approved", nullable=False),
        sa.Column("moderation_reason", sa.Text(), nullable=True),
        sa.Column("moderated_by_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("moderated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_review_replies_review_id"), "review_replies", ["review_id"])

    op.create_table(
        "review_flags",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("review_id", sa.UUID(as_uuid=True), sa.ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("flagged_by_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("resolved_by_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_review_flags_review_id"), "review_flags", ["review_id"])

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE reviews ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE reviews FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY reviews_isolation ON reviews FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM family_members fm
                    WHERE fm.id = reviews.member_id
                      AND fm.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE review_replies ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE review_replies FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY review_replies_isolation ON review_replies FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM reviews r
                    JOIN family_members fm ON fm.id = r.member_id
                    WHERE r.id = review_replies.review_id
                      AND fm.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE review_flags ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE review_flags FORCE ROW LEVEL SECURITY"))
    conn.execute(sa.text("CREATE POLICY review_flags_admin ON review_flags FOR ALL USING (current_setting('app.bypass_rls', true) = 'on')"))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DROP POLICY IF EXISTS review_flags_admin ON review_flags"))
    conn.execute(sa.text("ALTER TABLE review_flags DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS review_replies_isolation ON review_replies"))
    conn.execute(sa.text("ALTER TABLE review_replies DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS reviews_isolation ON reviews"))
    conn.execute(sa.text("ALTER TABLE reviews DISABLE ROW LEVEL SECURITY"))
    op.drop_index(op.f("ix_review_flags_review_id"), table_name="review_flags")
    op.drop_table("review_flags")
    op.drop_index(op.f("ix_review_replies_review_id"), table_name="review_replies")
    op.drop_table("review_replies")
    op.drop_index("ix_reviews_provider_status", table_name="reviews")
    op.drop_index(op.f("ix_reviews_author_user_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_member_id"), table_name="reviews")
    op.drop_index(op.f("ix_reviews_provider_profile_id"), table_name="reviews")
    op.drop_table("reviews")
