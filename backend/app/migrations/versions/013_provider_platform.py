"""create provider_profiles, doctor_details, lab_details, provider_claims, doctor_availability"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "013_provider_platform"
down_revision = "012_visibility_and_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_type", sa.String(32), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("photo_url", sa.String(255), nullable=True),
        sa.Column("license_number", sa.String(120), nullable=True),
        sa.Column("years_experience", sa.Integer(), nullable=True),
        sa.Column("consultation_fee_paise", sa.Integer(), nullable=True),
        sa.Column("verification_status", sa.String(32), server_default="unverified", nullable=False),
        sa.Column("verification_notes", sa.Text(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_provider_profiles_user"),
        sa.UniqueConstraint("slug", name="uq_provider_profiles_slug"),
    )
    op.create_index("ix_provider_profiles_user_id", "provider_profiles", ["user_id"], unique=False)
    op.create_index("ix_provider_profiles_slug", "provider_profiles", ["slug"], unique=False)

    op.create_table(
        "doctor_details",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_profile_id", UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("registration_number", sa.String(120), nullable=True),
        sa.Column("qualifications", sa.Text(), nullable=True),
        sa.Column("specializations", sa.Text(), nullable=True),
        sa.Column("languages", sa.String(255), nullable=True),
        sa.Column("teleconsult_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("home_visit_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider_profile_id", name="uq_doctor_details_profile"),
    )
    op.create_index("ix_doctor_details_profile_id", "doctor_details", ["provider_profile_id"], unique=True)

    op.create_table(
        "lab_details",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_profile_id", UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accreditation", sa.String(255), nullable=True),
        sa.Column("home_collection_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("report_turnaround_hours", sa.Integer(), nullable=True),
        sa.Column("serviceable_pincodes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider_profile_id", name="uq_lab_details_profile"),
    )
    op.create_index("ix_lab_details_profile_id", "lab_details", ["provider_profile_id"], unique=True)

    op.create_table(
        "provider_claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("profile_id", UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claimed_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("reviewed_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_provider_claims_profile_id", "provider_claims", ["profile_id"], unique=False)
    op.create_index("ix_provider_claims_claimed_by", "provider_claims", ["claimed_by_user_id"], unique=False)

    op.create_table(
        "doctor_availability",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("provider_profile_id", UUID(as_uuid=True), sa.ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.String(8), nullable=False),
        sa.Column("end_time", sa.String(8), nullable=False),
        sa.Column("slot_duration_minutes", sa.Integer(), server_default="30", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_doctor_availability_profile_id", "doctor_availability", ["provider_profile_id"], unique=False)


def downgrade() -> None:
    op.drop_table("doctor_availability")
    op.drop_table("provider_claims")
    op.drop_table("lab_details")
    op.drop_table("doctor_details")
    op.drop_table("provider_profiles")
