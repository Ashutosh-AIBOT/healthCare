"""Add xomni, nutrition, fitness, and timetable points tables.

Revision ID: 022_xomni_nutrition_fitness
Revises: 021_learn_embeddings
Create Date: 2026-09-08 11:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "022_xomni_nutrition_fitness"
down_revision: Union[str, None] = "021_learn_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- xomni_conversations ----
    op.create_table(
        "xomni_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False, server_default="New Chat"),
        sa.Column("mode", sa.String(40), nullable=False, server_default="general"),
        sa.Column("telegram_chat_id", sa.String(60), nullable=True),
        sa.Column("user_prompt_prefix", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_xomni_conversations_user_id", "xomni_conversations", ["user_id"])
    op.create_index("ix_xomni_conversations_telegram_chat_id", "xomni_conversations", ["telegram_chat_id"])

    # ---- xomni_messages ----
    op.create_table(
        "xomni_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("xomni_conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("audio_url", sa.String(500), nullable=True),
        sa.Column("citations", postgresql.JSONB, nullable=True),
        sa.Column("tokens_used", sa.Integer, nullable=True),
        sa.Column("provider_used", sa.String(40), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_xomni_messages_conversation_id", "xomni_messages", ["conversation_id"])

    # ---- nutrition_profiles ----
    op.create_table(
        "nutrition_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("height_cm", sa.Float, nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("age", sa.Integer, nullable=True),
        sa.Column("gender", sa.String(10), nullable=True),
        sa.Column("activity_level", sa.String(20), nullable=True),
        sa.Column("goal", sa.String(20), nullable=True),
        sa.Column("diet_type", sa.String(20), nullable=True),
        sa.Column("bmi", sa.Float, nullable=True),
        sa.Column("bmr_calories", sa.Integer, nullable=True),
        sa.Column("tdee_calories", sa.Integer, nullable=True),
        sa.Column("target_protein_g", sa.Integer, nullable=True),
        sa.Column("target_carbs_g", sa.Integer, nullable=True),
        sa.Column("target_fat_g", sa.Integer, nullable=True),
        sa.Column("user_restrictions", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_nutrition_profiles_user_id", "nutrition_profiles", ["user_id"])

    # ---- meal_plans ----
    op.create_table(
        "meal_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nutrition_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_json", postgresql.JSONB, nullable=True),
        sa.Column("ai_generated", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_meal_plans_user_id", "meal_plans", ["user_id"])

    # ---- fitness_profiles ----
    op.create_table(
        "fitness_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("level", sa.Integer, nullable=False, server_default="1"),
        sa.Column("goal_type", sa.String(40), nullable=True),
        sa.Column("target_weight_kg", sa.Float, nullable=True),
        sa.Column("target_body_fat_pct", sa.Float, nullable=True),
        sa.Column("target_date", sa.Date, nullable=True),
        sa.Column("weekly_workout_days", sa.Integer, nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_fitness_profiles_user_id", "fitness_profiles", ["user_id"])

    # ---- activity_logs ----
    op.create_table(
        "activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("activity_type", sa.String(80), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False),
        sa.Column("calories_burned", sa.Integer, nullable=True),
        sa.Column("distance_km", sa.Float, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("logged_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_activity_logs_user_id", "activity_logs", ["user_id"])
    op.create_index("ix_activity_logs_logged_date", "activity_logs", ["logged_date"])

    # ---- time_block_logs ----
    op.create_table(
        "time_block_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("block_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("time_blocks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("log_date", sa.Date, nullable=False),
        sa.Column("actual_activity", sa.Text, nullable=True),
        sa.Column("matched", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("completed_on_time", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("points_earned", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bonus_points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("outcome", sa.String(20), nullable=False, server_default="done"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_time_block_logs_user_id", "time_block_logs", ["user_id"])
    op.create_index("ix_time_block_logs_log_date", "time_block_logs", ["log_date"])
    op.create_index("ix_time_block_logs_block_id", "time_block_logs", ["block_id"])

    # ---- daily_points ----
    op.create_table(
        "daily_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("points_date", sa.Date, nullable=False),
        sa.Column("total_points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_possible", sa.Integer, nullable=False, server_default="100"),
        sa.Column("bonus_points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("penalty_points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("efficiency_pct", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("blocks_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("blocks_skipped", sa.Integer, nullable=False, server_default="0"),
        sa.Column("blocks_total", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_daily_points_user_id", "daily_points", ["user_id"])
    op.create_index("ix_daily_points_points_date", "daily_points", ["points_date"])
    op.create_unique_constraint("uq_daily_points_user_date", "daily_points", ["user_id", "points_date"])


def downgrade() -> None:
    op.drop_table("daily_points")
    op.drop_table("time_block_logs")
    op.drop_table("activity_logs")
    op.drop_table("fitness_profiles")
    op.drop_table("meal_plans")
    op.drop_table("nutrition_profiles")
    op.drop_table("xomni_messages")
    op.drop_table("xomni_conversations")
