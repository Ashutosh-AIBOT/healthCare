"""visibility grants, claims, access logs, documents, dual-consent transfer columns

Revision ID: 012
Revises: 011
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# PLAN §7.11 seed: relationship → field keys (all at level view)
_VISIBILITY_DEFAULTS: list[tuple[str, tuple[str, ...]]] = [
    (
        "guardian",
        (
            "vitals",
            "lab_results",
            "conditions",
            "medications",
            "prescriptions",
            "nutrition",
            "activity",
            "tasks",
            "appointments",
            "health_score",
            "documents",
        ),
    ),
    ("spouse", ("health_score", "activity", "nutrition", "appointments")),
    ("adult_child", ("health_score", "appointments")),
    ("parent", ("health_score", "appointments")),
    ("sibling", ("health_score", "activity")),
]


def upgrade() -> None:
    op.create_table(
        "member_visibility_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "subject_member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("family_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "viewer_member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("family_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_key", sa.String(64), nullable=False),
        sa.Column("level", sa.String(32), nullable=False, server_default="view"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "subject_member_id",
            "viewer_member_id",
            "field_key",
            name="uq_visibility_grant_subject_viewer_field",
        ),
    )
    op.create_index("ix_member_visibility_grants_subject_member_id", "member_visibility_grants", ["subject_member_id"])
    op.create_index("ix_member_visibility_grants_viewer_member_id", "member_visibility_grants", ["viewer_member_id"])

    op.create_table(
        "visibility_defaults",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("relationship", sa.String(64), nullable=False),
        sa.Column("field_key", sa.String(64), nullable=False),
        sa.Column("level", sa.String(32), nullable=False, server_default="view"),
        sa.UniqueConstraint("relationship", "field_key", name="uq_visibility_default_rel_field"),
    )

    op.create_table(
        "member_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("family_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "invited_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "claiming_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("confirm_full_name", sa.String(120), nullable=True),
        sa.Column("confirm_dob", sa.String(32), nullable=True),
        sa.Column("guardian_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("member_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_member_claims_member_id", "member_claims", ["member_id"])

    op.create_table(
        "consent_access_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "subject_member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("family_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "viewer_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_key", sa.String(64), nullable=False),
        sa.Column("purpose", sa.String(120), nullable=False, server_default="family_read"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.Text(), nullable=True),
    )
    op.create_index("ix_consent_access_logs_subject_member_id", "consent_access_logs", ["subject_member_id"])
    op.create_index("ix_consent_access_logs_viewer_user_id", "consent_access_logs", ["viewer_user_id"])

    # M4 document / job tables
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("result", postgresql.JSONB(), nullable=True),
        sa.Column("idempotency_key", sa.String(120), nullable=True, unique=True),
    )
    op.create_index("ix_jobs_family_id", "jobs", ["family_id"])

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("family_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False, server_default="application/pdf"),
        sa.Column("byte_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="uploaded"),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_documents_family_id", "documents", ["family_id"])
    op.create_index("ix_documents_member_id", "documents", ["member_id"])

    op.create_table(
        "lab_report_values",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("family_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("analyte_code", sa.String(64), nullable=False),
        sa.Column("analyte_name", sa.String(120), nullable=False),
        sa.Column("value_num", sa.Float(), nullable=True),
        sa.Column("value_text", sa.String(120), nullable=True),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("ref_low", sa.Float(), nullable=True),
        sa.Column("ref_high", sa.Float(), nullable=True),
        sa.Column("flag", sa.String(32), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.9"),
        sa.Column("page", sa.Integer(), nullable=True),
    )
    op.create_index("ix_lab_report_values_document_id", "lab_report_values", ["document_id"])
    op.create_index("ix_lab_report_values_member_id", "lab_report_values", ["member_id"])
    op.create_index("ix_lab_report_values_family_id", "lab_report_values", ["family_id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "family_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "member_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("family_members.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=True),
        sa.Column("embedding", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_family_id", "document_chunks", ["family_id"])
    op.create_index("ix_document_chunks_member_id", "document_chunks", ["member_id"])

    # Dual-consent columns on member_transfers
    op.add_column(
        "member_transfers",
        sa.Column("from_family_confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "member_transfers",
        sa.Column("to_family_confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_member_transfers_from_family_confirmed_by",
        "member_transfers",
        "users",
        ["from_family_confirmed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_member_transfers_to_family_confirmed_by",
        "member_transfers",
        "users",
        ["to_family_confirmed_by"],
        ["id"],
        ondelete="SET NULL",
    )

    # Seed visibility_defaults
    values_sql = []
    for relationship, fields in _VISIBILITY_DEFAULTS:
        for field_key in fields:
            values_sql.append(
                f"(gen_random_uuid(), '{relationship}', '{field_key}', 'view', NOW(), NOW())"
            )
    op.execute(
        sa.text(
            "INSERT INTO visibility_defaults (id, relationship, field_key, level, created_at, updated_at) VALUES "
            + ", ".join(values_sql)
        )
    )

    # RLS — family_id where present; grants/claims/logs via subject membership family
    conn = op.get_bind()
    family_id_tables = ("jobs", "documents", "lab_report_values", "document_chunks")
    for table in family_id_tables:
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        conn.execute(
            sa.text(
                f"""
                CREATE POLICY {table}_isolation ON {table} FOR ALL
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

    for table, member_col in (
        ("member_visibility_grants", "subject_member_id"),
        ("member_claims", "member_id"),
        ("consent_access_logs", "subject_member_id"),
    ):
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        conn.execute(
            sa.text(
                f"""
                CREATE POLICY {table}_isolation ON {table} FOR ALL
                USING (
                    current_setting('app.bypass_rls', true) = 'on'
                    OR EXISTS (
                        SELECT 1 FROM family_members fm
                        WHERE fm.id = {table}.{member_col}
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
    for table in (
        "consent_access_logs",
        "member_claims",
        "member_visibility_grants",
        "document_chunks",
        "lab_report_values",
        "documents",
        "jobs",
    ):
        conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_isolation ON {table}"))
        conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    op.drop_constraint("fk_member_transfers_to_family_confirmed_by", "member_transfers", type_="foreignkey")
    op.drop_constraint("fk_member_transfers_from_family_confirmed_by", "member_transfers", type_="foreignkey")
    op.drop_column("member_transfers", "to_family_confirmed_by")
    op.drop_column("member_transfers", "from_family_confirmed_by")

    op.drop_table("document_chunks")
    op.drop_table("lab_report_values")
    op.drop_table("documents")
    op.drop_table("jobs")
    op.drop_table("consent_access_logs")
    op.drop_table("member_claims")
    op.drop_table("visibility_defaults")
    op.drop_table("member_visibility_grants")
