"""create appointments and appointment_events tables

Revision ID: 015
Revises: 014
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("family_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", sa.String(16), server_default="in_person", nullable=False),
        sa.Column("status", sa.String(32), server_default="requested", nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("patient_notes", sa.Text(), nullable=True),
        sa.Column("provider_notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("fee_paise", sa.Integer(), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(120), nullable=True),
        sa.CheckConstraint("scheduled_end > scheduled_start", name="ck_appointments_time_order"),
    )
    op.create_index("ix_appointments_family_id", "appointments", ["family_id"])
    op.create_index("ix_appointments_member_id", "appointments", ["member_id"])
    op.create_index(
        "ix_appointments_provider_profile_id", "appointments", ["provider_profile_id"]
    )
    op.create_index("ix_appointments_status", "appointments", ["status"])
    op.create_index("ix_appointments_scheduled_start", "appointments", ["scheduled_start"])
    op.create_index("ix_appointments_idempotency_key", "appointments", ["idempotency_key"])
    op.create_index("ix_appointments_family_status", "appointments", ["family_id", "status"])
    op.create_index(
        "ix_appointments_provider_scheduled", "appointments", ["provider_profile_id", "scheduled_start"]
    )
    # Partial unique index: prevent double-booking only while a slot is still
    # in flight. Terminal statuses are excluded so cancelled/completed rows
    # never block future bookings.
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX uq_appointments_provider_slot_active
            ON appointments (provider_profile_id, scheduled_start)
            WHERE status NOT IN (
                'completed', 'declined', 'expired',
                'cancelled_by_patient', 'cancelled_by_provider',
                'no_show_patient', 'no_show_provider'
            )
            """
        )
    )

    op.create_table(
        "appointment_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_role", sa.String(32), nullable=False),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_appointment_events_appointment_id", "appointment_events", ["appointment_id"])

    # RLS — appointments: tenant is the booking family. Providers view their own
    # bookings via a separate provider-scoped session (set app.bypass_rls = on
    # for provider dashboards until a provider tenant context exists).
    conn.execute(sa.text("ALTER TABLE appointments ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE appointments FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY appointments_isolation ON appointments FOR ALL
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

    conn.execute(sa.text("ALTER TABLE appointment_events ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE appointment_events FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY appointment_events_isolation ON appointment_events FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM appointments a
                    WHERE a.id = appointment_events.appointment_id
                      AND a.family_id = COALESCE(
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
    conn.execute(sa.text("DROP INDEX IF EXISTS uq_appointments_provider_slot_active"))
    conn.execute(sa.text("DROP POLICY IF EXISTS appointment_events_isolation ON appointment_events"))
    conn.execute(sa.text("ALTER TABLE appointment_events DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS appointments_isolation ON appointments"))
    conn.execute(sa.text("ALTER TABLE appointments DISABLE ROW LEVEL SECURITY"))
    op.drop_table("appointment_events")
    op.drop_index("ix_appointments_provider_scheduled", table_name="appointments")
    op.drop_index("ix_appointments_family_status", table_name="appointments")
    op.drop_index("ix_appointments_idempotency_key", table_name="appointments")
    op.drop_index("ix_appointments_scheduled_start", table_name="appointments")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_provider_profile_id", table_name="appointments")
    op.drop_index("ix_appointments_member_id", table_name="appointments")
    op.drop_index("ix_appointments_family_id", table_name="appointments")
    op.drop_table("appointments")
