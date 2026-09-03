"""Nutrition models (M13).

Stores food items, logged meals, nutrition targets and generated diet plans.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


class FoodItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_items"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    serving_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    calories_kcal: Mapped[float | None] = mapped_column(Integer, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    glycemic_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)


class MealType:
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class FoodLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "food_logs"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    food_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("food_items.id", ondelete="SET NULL"), nullable=True
    )
    meal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Integer, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    calories_kcal: Mapped[float | None] = mapped_column(Integer, nullable=True)
    protein_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    carbs_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    fat_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    fiber_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str | None] = mapped_column(String(32), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_estimate: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    member: Mapped["FamilyMember"] = relationship()
    food_item: Mapped["FoodItem | None"] = relationship()


class NutritionTarget(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_targets"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    daily_calories_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_protein_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    daily_carbs_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    daily_fat_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    daily_fiber_g: Mapped[float | None] = mapped_column(Integer, nullable=True)
    max_glycemic_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    member: Mapped["FamilyMember"] = relationship()


class NutritionPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_plans"

    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Integer, default=1, nullable=False)

    member: Mapped["FamilyMember"] = relationship()
