"""Module 4 Dashboard scoring service.

Aggregates the user's vitals/nutrition/workout activity from the last 7 days
into a single composite score plus sub-scores. Each user has exactly one
UserScore row; widget visibility and chatbot toggle live alongside.

Scoring rules (defaults):
- time_management_score: 0 (placeholder; module not built yet)
- diet_score: ratio of recent food logs to 7 daily targets (0..100)
- fitness_score: blend of workout session count and recent vital recency (0..100)
- composite_score: equal-weighted mean of the three sub-scores (0..100)

All queries respect the active Postgres RLS tenant context. The summary
endpoint caches the aggregate in Redis with a short TTL so the highest-
traffic page on the app stays under its p95 < 200ms target.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dashboard import (
    DEFAULT_WIDGET_VISIBILITY,
    UserScore,
)
from app.models.user import User
from app.schemas.dashboard import DashboardPreferences, DashboardSummary

logger = logging.getLogger(__name__)

SUMMARY_CACHE_TTL_SECONDS = 60
SCORE_WINDOW_DAYS = 7
EQUAL_WEIGHT = 1.0 / 3.0


class DashboardService:
    @staticmethod
    def _summary_cache_key(user_id: uuid.UUID) -> str:
        return f"dashboard:summary:{user_id}"

    async def _cache_get(self, user_id: uuid.UUID) -> dict | None:
        try:
            import redis.asyncio as redis
            client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)
            try:
                raw = await client.get(self._summary_cache_key(user_id))
            finally:
                await client.aclose()
        except Exception:
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def _cache_set(self, user_id: uuid.UUID, payload: dict) -> None:
        try:
            import redis.asyncio as redis
            client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)
            try:
                await client.setex(
                    self._summary_cache_key(user_id),
                    SUMMARY_CACHE_TTL_SECONDS,
                    json.dumps(payload, default=str),
                )
            finally:
                await client.aclose()
        except Exception:
            return

    async def _cache_invalidate(self, user_id: uuid.UUID) -> None:
        try:
            import redis.asyncio as redis
            client = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)
            try:
                await client.delete(self._summary_cache_key(user_id))
            finally:
                await client.aclose()
        except Exception:
            return

    async def get_or_create_score(self, db: AsyncSession, user_id: uuid.UUID) -> UserScore:
        user = await db.get(User, user_id)
        if user is None:
            from app.core.errors import AppError
            raise AppError(code="USER_NOT_FOUND", status=404, detail="User not found.")

        result = await db.execute(select(UserScore).where(UserScore.user_id == user_id))
        score = result.scalar_one_or_none()
        if score is not None:
            return score

        score = UserScore(
            user_id=user_id,
            composite_score=0.0,
            time_management_score=0.0,
            diet_score=0.0,
            fitness_score=0.0,
            widget_visibility=dict(DEFAULT_WIDGET_VISIBILITY),
            chatbot_toggle_state=False,
            last_recomputed_at=None,
        )
        db.add(score)
        await db.flush()
        return score

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, value))

    async def _recent_food_log_days(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        """Count distinct days in last 7d with at least one food_log entry.

        Falls back to 0 if the table is not present (M6 module may not be built).
        """
        cutoff = datetime.now(UTC) - timedelta(days=SCORE_WINDOW_DAYS)
        sql = text(
            """
            SELECT COUNT(DISTINCT date_trunc('day', logged_at)) AS day_count
            FROM food_logs
            WHERE user_id = :user_id
              AND logged_at >= :cutoff
            """
        )
        try:
            result = await db.execute(sql, {"user_id": str(user_id), "cutoff": cutoff})
            row = result.first()
        except Exception:
            logger.warning("food_logs unavailable for user_id=%s; diet_score=0", user_id)
            return 0
        if row is None or row[0] is None:
            return 0
        return int(row[0])

    async def _recent_workout_count(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        """Count workout sessions in last 7d. Falls back to 0 if table missing."""
        cutoff = datetime.now(UTC) - timedelta(days=SCORE_WINDOW_DAYS)
        sql = text(
            """
            SELECT COUNT(*) FROM workout_sessions
            WHERE user_id = :user_id
              AND performed_at >= :cutoff
            """
        )
        try:
            result = await db.execute(sql, {"user_id": str(user_id), "cutoff": cutoff})
            row = result.first()
        except Exception:
            logger.warning("workout_sessions unavailable for user_id=%s; fitness_score=0", user_id)
            return 0
        return int(row[0]) if row and row[0] is not None else 0

    async def _recent_vital_count(self, db: AsyncSession, user_id: uuid.UUID) -> int:
        """Count vital readings in last 7d. Falls back to 0 if table missing."""
        cutoff = datetime.now(UTC) - timedelta(days=SCORE_WINDOW_DAYS)
        sql = text(
            """
            SELECT COUNT(*) FROM vitals
            WHERE user_id = :user_id
              AND measured_at >= :cutoff
            """
        )
        try:
            result = await db.execute(sql, {"user_id": str(user_id), "cutoff": cutoff})
            row = result.first()
        except Exception:
            logger.warning("vitals unavailable for user_id=%s; fitness_score=0", user_id)
            return 0
        return int(row[0]) if row and row[0] is not None else 0

    async def _compute_sub_scores(self, db: AsyncSession, user_id: uuid.UUID) -> tuple[float, float, float]:
        time_management = 0.0  # Placeholder until the module ships.

        food_days = await self._recent_food_log_days(db, user_id)
        diet = self._clamp((food_days / SCORE_WINDOW_DAYS) * 100.0)

        workouts = await self._recent_workout_count(db, user_id)
        vitals = await self._recent_vital_count(db, user_id)
        # 5 sessions/week ≈ perfect; cap at 100. Vitals contribute a small bonus
        # (up to 20 points) to reward routine measurement.
        workout_component = self._clamp((workouts / 5.0) * 80.0)
        vitals_component = self._clamp(min(vitals, 7) * (20.0 / 7.0))
        fitness = self._clamp(workout_component + vitals_component)

        return time_management, diet, fitness

    async def recompute_scores(self, db: AsyncSession, user_id: uuid.UUID) -> UserScore:
        score = await self.get_or_create_score(db, user_id)
        time_mgmt, diet, fitness = await self._compute_sub_scores(db, user_id)
        composite = self._clamp(time_mgmt * EQUAL_WEIGHT + diet * EQUAL_WEIGHT + fitness * EQUAL_WEIGHT)
        now = datetime.now(UTC)
        score.time_management_score = round(time_mgmt, 2)
        score.diet_score = round(diet, 2)
        score.fitness_score = round(fitness, 2)
        score.composite_score = round(composite, 2)
        score.last_recomputed_at = now
        await db.flush()
        await self._cache_invalidate(user_id)
        return score

    async def update_preferences(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: DashboardPreferences,
    ) -> UserScore:
        score = await self.get_or_create_score(db, user_id)
        if payload.widget_visibility:
            score.widget_visibility = DashboardPreferences.normalize_widgets(payload.widget_visibility)
        if payload.chatbot_toggle_state is not None:
            score.chatbot_toggle_state = payload.chatbot_toggle_state
        await db.flush()
        await self._cache_invalidate(user_id)
        return score

    async def get_summary(self, db: AsyncSession, user_id: uuid.UUID) -> DashboardSummary:
        cached = await self._cache_get(user_id)
        if cached is not None:
            return DashboardSummary(**cached)

        score = await self.get_or_create_score(db, user_id)
        # If scores have never been computed, compute once so the first
        # dashboard load is not all zeros on day 1.
        if score.last_recomputed_at is None:
            score = await self.recompute_scores(db, user_id)

        summary = DashboardSummary(
            user_id=str(score.user_id),
            composite_score=score.composite_score,
            time_management_score=score.time_management_score,
            diet_score=score.diet_score,
            fitness_score=score.fitness_score,
            widget_visibility=score.widget_visibility or dict(DEFAULT_WIDGET_VISIBILITY),
            chatbot_toggle_state=score.chatbot_toggle_state,
            last_recomputed_at=score.last_recomputed_at,
        )
        await self._cache_set(user_id, summary.model_dump())
        return summary


dashboard_service = DashboardService()
