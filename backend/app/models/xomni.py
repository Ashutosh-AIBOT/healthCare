"""Xomni AI chat models: conversations, messages, nutrition profile, meal plans, fitness."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.session import TimestampMixin, UUIDPrimaryKeyMixin


# ---------------------------------------------------------------------------
# Xomni Chat
# ---------------------------------------------------------------------------

class XomniConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "xomni_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="New Chat")
    mode: Mapped[str] = mapped_column(String(40), nullable=False, default="general")
    # mode: general | food | timetable | reports | fitness
    telegram_chat_id: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    user_prompt_prefix: Mapped[str | None] = mapped_column(Text, nullable=True)
    # User's persistent instructions / dietary restrictions

    messages: Mapped[list["XomniMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan",
        order_by="XomniMessage.created_at"
    )


class XomniMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "xomni_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("xomni_conversations.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(40), nullable=True)

    conversation: Mapped["XomniConversation"] = relationship(back_populates="messages")


# ---------------------------------------------------------------------------
# Nutrition / BMI
# ---------------------------------------------------------------------------

class NutritionProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "nutrition_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)  # male | female | other
    activity_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # sedentary | lightly_active | moderately_active | very_active | extra_active
    goal: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # lose_weight | maintain | gain_muscle
    diet_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # veg | non_veg | vegan | eggetarian
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)
    bmr_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Basal metabolic rate
    tdee_calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Total daily energy expenditure
    target_protein_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_carbs_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_fat_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free text: allergies, dislikes, etc.


class MealPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_plans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("nutrition_profiles.id", ondelete="SET NULL"),
        nullable=True
    )
    plan_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Structured: {breakfast: [...], lunch: [...], dinner: [...], snacks: [...], fruits: [...]}
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(20), nullable=False, default="USER")  # "USER" or "XOMNI"
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class MealPlanHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "meal_plan_histories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    meal_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meal_plans.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    plan_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Fitness
# ---------------------------------------------------------------------------

class FitnessProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fitness_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True
    )
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 1 = Beginner/Weight Loss, 2 = Intermediate/Muscle Build, 3 = Advanced/Athletic
    goal_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # weight_loss | muscle_build | endurance | general_fitness | athletic
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    weekly_workout_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)


class ActivityLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "activity_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    activity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    # running | cycling | swimming | strength | yoga | walking | other
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    calories_burned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logged_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)


# ---------------------------------------------------------------------------
# Timetable Points
# ---------------------------------------------------------------------------

class TimeBlockLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks what user actually did vs. planned, and points awarded."""
    __tablename__ = "time_block_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    block_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("time_blocks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    actual_activity: Mapped[str | None] = mapped_column(Text, nullable=True)
    # What the user actually did (compared to planned)
    matched: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # True if actual matches the planned task
    completed_on_time: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    points_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bonus_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False, default="done")
    # done | skipped | partial


class DailyPoints(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Aggregated daily points summary per user."""
    __tablename__ = "daily_points"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    points_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_possible: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    bonus_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    penalty_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    efficiency_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    blocks_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocks_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocks_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
