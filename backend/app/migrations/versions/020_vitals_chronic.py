"""create vitals, chronic_programs and adherence_records tables

Revision ID: 020
Revises: 019
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vitals",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("member_id", sa.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recorded_by_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("height_mm", sa.Integer(), nullable=True),
        sa.Column("temperature_decidegrees_celsius", sa.Integer(), nullable=True),
        sa.Column("systolic_bp_mmhg", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp_mmhg", sa.Integer(), nullable=True),
        sa.Column("heart_rate_bpm", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("device_id", sa.String(length=120), nullable=True),
    )
    op.create_index(op.f("ix_vitals_member_id"), "vitals", ["member_id"])

    op.create_table(
        "chronic_programs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("member_id", sa.UUID(as_uuid=True), sa.ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False),
        sa.Column("program_type", sa.String(length=32), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_systolic_bp", sa.Integer(), nullable=True),
        sa.Column("target_diastolic_bp", sa.Integer(), nullable=True),
        sa.Column("target_hba1c_percent", sa.Integer(), nullable=True),
        sa.Column("target_weight_grams", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_chronic_programs_member_id"), "chronic_programs", ["member_id"])

    op.create_table(
        "adherence_records",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("program_id", sa.UUID(as_uuid=True), sa.ForeignKey("chronic_programs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_compliant", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_adherence_records_program_id"), "adherence_records", ["program_id"])

    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE vitals ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE vitals FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY vitals_isolation ON vitals FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM family_members fm
                    WHERE fm.id = vitals.member_id
                      AND fm.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE chronic_programs ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE chronic_programs FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY chronic_programs_isolation ON chronic_programs FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM family_members fm
                    WHERE fm.id = chronic_programs.member_id
                      AND fm.family_id = COALESCE(
                          NULLIF(current_setting('app.family_id', true), '')::uuid,
                          '00000000-0000-0000-0000-000000000000'
                      )
                )
            )
            """
        )
    )

    conn.execute(sa.text("ALTER TABLE adherence_records ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("ALTER TABLE adherence_records FORCE ROW LEVEL SECURITY"))
    conn.execute(
        sa.text(
            """
            CREATE POLICY adherence_records_isolation ON adherence_records FOR ALL
            USING (
                current_setting('app.bypass_rls', true) = 'on'
                OR EXISTS (
                    SELECT 1 FROM chronic_programs cp
                    JOIN family_members fm ON fm.id = cp.member_id
                    WHERE cp.id = adherence_records.program_id
                      AND fm.family_id = COALESCE(
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
    conn.execute(sa.text("DROP POLICY IF EXISTS adherence_records_isolation ON adherence_records"))
    conn.execute(sa.text("ALTER TABLE adherence_records DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS chronic_programs_isolation ON chronic_programs"))
    conn.execute(sa.text("ALTER TABLE chronic_programs DISABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("DROP POLICY IF EXISTS vitals_isolation ON vitals"))
    conn.execute(sa.text("ALTER TABLE vitals DISABLE ROW LEVEL SECURITY"))
    op.drop_index(op.f("ix_adherence_records_program_id"), table_name="adherence_records")
    op.drop_table("adherence_records")
    op.drop_index(op.f("ix_chronic_programs_member_id"), table_name="chronic_programs")
    op.drop_table("chronic_programs")
    op.drop_index(op.f("ix_vitals_member_id"), table_name="vitals")
    op.drop_table("vitals")
