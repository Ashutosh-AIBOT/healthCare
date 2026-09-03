import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin
from app.models.user import User


class ProviderProfile(TimestampMixin, Base):
    __tablename__ = "provider_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    license_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consultation_fee_paise: Mapped[int | None] = mapped_column(Integer, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="unverified", nullable=False)
    verification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str] = mapped_column(String(120), default="India", nullable=False)
    pincode: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    response_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    verified_by: Mapped["User | None"] = relationship(foreign_keys=[verified_by_user_id])
    doctor_details: Mapped["DoctorDetail | None"] = relationship(back_populates="profile", cascade="all, delete-orphan")
    lab_details: Mapped["LabDetail | None"] = relationship(back_populates="profile", cascade="all, delete-orphan")
    claims: Mapped[list["ProviderClaim"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    availabilities: Mapped[list["DoctorAvailability"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class DoctorDetail(TimestampMixin, Base):
    __tablename__ = "doctor_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    registration_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    qualifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    specializations: Mapped[str | None] = mapped_column(Text, nullable=True)
    languages: Mapped[str | None] = mapped_column(String(255), nullable=True)
    teleconsult_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    home_visit_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    profile: Mapped["ProviderProfile"] = relationship(back_populates="doctor_details")


class LabDetail(TimestampMixin, Base):
    __tablename__ = "lab_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    accreditation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    home_collection_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    report_turnaround_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    serviceable_pincodes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped["ProviderProfile"] = relationship(back_populates="lab_details")


class ProviderClaim(TimestampMixin, Base):
    __tablename__ = "provider_claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claimed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile: Mapped["ProviderProfile"] = relationship(back_populates="claims")
    claimed_by: Mapped["User"] = relationship(foreign_keys=[claimed_by_user_id])
    reviewed_by: Mapped["User | None"] = relationship(foreign_keys=[reviewed_by_user_id])


class DoctorAvailability(TimestampMixin, Base):
    __tablename__ = "doctor_availability"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provider_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[str] = mapped_column(String(8), nullable=False)
    end_time: Mapped[str] = mapped_column(String(8), nullable=False)
    slot_duration_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profile: Mapped["ProviderProfile"] = relationship(back_populates="availabilities")
