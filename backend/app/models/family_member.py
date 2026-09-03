import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin
from app.models.family import Family
from app.models.user import User


class Relation:
    FATHER = "father"
    MOTHER = "mother"
    SPOUSE = "spouse"
    SON = "son"
    DAUGHTER = "daughter"
    BROTHER = "brother"
    SISTER = "sister"
    GRANDFATHER = "grandfather"
    GRANDMOTHER = "grandmother"
    OTHER = "other"


class Gender:
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class BloodGroup:
    A_POS = "a_pos"
    A_NEG = "a_neg"
    B_POS = "b_pos"
    B_NEG = "b_neg"
    AB_POS = "ab_pos"
    AB_NEG = "ab_neg"
    O_POS = "o_pos"
    O_NEG = "o_neg"
    UNKNOWN = "unknown"


class DietPreference:
    VEGETARIAN = "vegetarian"
    NON_VEGETARIAN = "non_vegetarian"
    EGGETARIAN = "eggetarian"
    VEGAN = "vegan"
    JAIN = "jain"


class FamilyMember(TimestampMixin, Base):
    __tablename__ = "family_members"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("families.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    relation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    date_of_birth: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_dependent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="SET NULL"), nullable=True, index=True
    )
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)
    diet_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    family: Mapped["Family"] = relationship(back_populates="family_members")
    user: Mapped["User | None"] = relationship()
    guardian: Mapped["FamilyMember | None"] = relationship(remote_side="FamilyMember.id")
    dependents: Mapped[list["FamilyMember"]] = relationship(back_populates="guardian")
    medical_profile: Mapped["MemberMedicalProfile | None"] = relationship(back_populates="member", cascade="all, delete-orphan")
