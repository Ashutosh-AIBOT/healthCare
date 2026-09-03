"""create teleconsult_sessions, prescriptions and prescription_items tables

Revision ID: 017
Revises: 016
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    op.create_table(
        "teleconsult_sessions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("appointment_id", sa.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("room_id", sa.String(length=120), nullable=True),
        sa.Column("room_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="scheduled", nullable=False),
        sa.Column("telemedicine_consent_recorded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recording_url", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_teleconsult_sessions_appointment_id"), "teleconsult_sessions", ["appointment_id"], unique=True)

    op.create_table(
        "prescriptions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("appointment_id", sa.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doctor_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_id", sa.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("signed_pdf_url", sa.Text(), nullable=True),
        sa.Column("registration_number", sa.String(length=120), nullable=True),
    )
    op.create_index(op.f("ix_prescriptions_appointment_id"), "prescriptions", ["appointment_id"], unique=True)
    op.create_index(op.f("ix_prescriptions_member_id"), "prescriptions", ["member_id"])

    op.create_table(
        "prescription_items",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("prescription_id", sa.UUID(as_uuid=True), sa.ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drug_name", sa.String(length=200), nullable=False),
        sa.Column("dosage", sa.String(length=120), nullable=True),
        sa.Column("frequency", sa.String(length=120), nullable=True),
        sa.Column("duration", sa.String(length=120), nullable=True),
        sa.Column("instructions", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_prescription_items_prescription_id"), "prescription_items", ["prescription_id"])

    conn.execute(sa.text("ALTER TABLE teleconsult_sessions ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE teleconsult_sessions FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY teleconsult_sessions_isolation ON teleconsult_sessions FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM appointments a
                    WHERE a.id = teleconsult_sessions.appointment_id
                      AND a.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE prescriptions ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE prescriptions FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY prescriptions_isolation ON prescriptions FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM appointments a
                    WHERE a.id = prescriptions.appointment_id
                      AND a.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE prescription_items ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE prescription_items FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY prescription_items_isolation ON prescription_items FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM prescriptions p
                    JOIN appointments a ON a.id = p.appointment_id
                    WHERE p.id = prescription_items.prescription_id
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
    conn.execute(sa.text("DROP POLICY IF EXISTS prescription_items_isolation ON prescription_items"))
    conn.execute(sa.text("ALTER TABLE prescription_items DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS prescriptions_isolation ON prescriptions"))
    conn.execute(sa.text("ALTER TABLE prescriptions DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS teleconsult_sessions_isolation ON teleconsult_sessions"))
    conn.execute(sa.text("ALTER TABLE teleconsult_sessions DISABLE ROW LEVEL SECURITY"))
    op.drop_index(op.f("ix_prescription_items_prescription_id"), table_name="prescription_items")
    op.drop_table("prescription_items")
    op.drop_index(op.f("ix_prescriptions_member_id"), table_name="prescriptions")
    op.drop_index(op.f("ix_prescriptions_appointment_id"), table_name="prescriptions")
    op.drop_table("prescriptions")
    op.drop_index(op.f("ix_teleconsult_sessions_appointment_id"), table_name="teleconsult_sessions")
    op.drop_table("teleconsult_sessions")
