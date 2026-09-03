"""create lab_bookings and lab_booking_events tables

Revision ID: 018
Revises: 017
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lab_bookings",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("family_id", sa.UUID(as_uuid=True), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_profile_id", sa.UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="requested", nullable=False),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("total_price_paise", sa.Integer(), nullable=True),
        sa.Column("collection_slot_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collection_slot_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collection_address", sa.Text(), nullable=True),
        sa.Column("home_collection", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("test_ids", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
    )
    op.create_index(op.f("ix_lab_bookings_family_id"), "lab_bookings", ["family_id"])
    op.create_index(op.f("ix_lab_bookings_member_id"), "lab_bookings", ["member_id"])
    op.create_index(op.f("ix_lab_bookings_provider_profile_id"), "lab_bookings", ["provider_profile_id"])
    op.create_index(op.f("ix_lab_bookings_status"), "lab_bookings", ["status"])
    op.create_index("ix_lab_bookings_family_status", "lab_bookings", ["family_id", "status"])
    op.create_index("ix_lab_bookings_provider_status", "lab_bookings", ["provider_profile_id", "status"])
    op.create_index(op.f("ix_lab_bookings_idempotency_key"), "lab_bookings", ["idempotency_key"], unique=True)
    op.create_check_constraint("ck_lab_bookings_collection_time_order", "lab_bookings", "collection_slot_end IS NULL OR collection_slot_end > collection_slot_start")

    op.create_table(
        "lab_booking_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("booking_id", sa.UUID(as_uuid=True), sa.ForeignKey("lab_bookings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=True),
        sa.Column("sample_event", sa.String(length=32), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_lab_booking_events_booking_id"), "lab_booking_events", ["booking_id"])

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE lab_bookings ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE lab_bookings FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY lab_bookings_isolation ON lab_bookings FOR ALL
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

    conn.execute(sa.text("ALTER TABLE lab_booking_events ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE lab_booking_events FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY lab_booking_events_isolation ON lab_booking_events FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM lab_bookings b
                    WHERE b.id = lab_booking_events.booking_id
                      AND b.family_id = COALESCE(
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
    conn.execute(sa.text("DROP POLICY IF EXISTS lab_booking_events_isolation ON lab_booking_events"))
    conn.execute(sa.text("ALTER TABLE lab_booking_events DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS lab_bookings_isolation ON lab_bookings"))
    conn.execute(sa.text("ALTER TABLE lab_bookings DISABLE ROW LEVEL SECURITY"))
    op.drop_index(op.f("ix_lab_bookings_idempotency_key"), table_name="lab_bookings")
    op.drop_index("ix_lab_bookings_provider_status", table_name="lab_bookings")
    op.drop_index("ix_lab_bookings_family_status", table_name="lab_bookings")
    op.drop_index(op.f("ix_lab_bookings_status"), table_name="lab_bookings")
    op.drop_index(op.f("ix_lab_bookings_provider_profile_id"), table_name="lab_bookings")
    op.drop_index(op.f("ix_lab_bookings_member_id"), table_name="lab_bookings")
    op.drop_index(op.f("ix_lab_bookings_family_id"), table_name="lab_bookings")
    op.drop_table("lab_bookings")
    op.drop_index(op.f("ix_lab_booking_events_booking_id"), table_name="lab_booking_events")
    op.drop_table("lab_booking_events")
