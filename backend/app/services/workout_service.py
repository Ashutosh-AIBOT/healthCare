"""Workout service (M14)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.family_member import FamilyMember
from app.models.workout import WorkoutPlan, WorkoutSession, WorkoutExercise

logger = logging.getLogger(__name__)


class WorkoutService:
    async def _get_member_for_family(self, db: AsyncSession, member_id: uuid.UUID, family_id: uuid.UUID) -> FamilyMember:
        result = await db.execute(
            select(FamilyMember).where(
                FamilyMember.id == member_id,
                FamilyMember.family_id == family_id,
                FamilyMember.deleted_at.is_(None),
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise AppError(code="MEMBER_NOT_FOUND", status=404, detail="Family member not found.")
        return member

    async def create_plan(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        member_id: uuid.UUID,
        payload,
    ) -> WorkoutPlan:
        await self._get_member_for_family(db, member_id, family_id)

        plan = WorkoutPlan(
            member_id=member_id,
            title=payload.title,
            description=payload.description,
            condition_notes=payload.condition_notes,
        )
        db.add(plan)
        await db.flush()
        logger.info("workout plan created plan_id=%s member_id=%s", plan.id, member_id)
        return plan

    async def list_plans(self, db: AsyncSession, family_id: uuid.UUID, member_id: uuid.UUID) -> list[WorkoutPlan]:
        await self._get_member_for_family(db, member_id, family_id)
        result = await db.execute(
            select(WorkoutPlan).where(WorkoutPlan.member_id == member_id).order_by(WorkoutPlan.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_session(
        self,
        db: AsyncSession,
        *,
        family_id: uuid.UUID,
        payload,
    ) -> WorkoutSession:
        plan = await db.get(WorkoutPlan, payload.plan_id)
        if plan is None:
            raise AppError(code="PLAN_NOT_FOUND", status=404, detail="Workout plan not found.")
        await self._get_member_for_family(db, plan.member_id, family_id)

        session = WorkoutSession(
            plan_id=payload.plan_id,
            title=payload.title,
            description=payload.description,
            scheduled_at=payload.scheduled_at,
            duration_minutes=payload.duration_minutes,
            calories_burned=payload.calories_burned,
            notes=payload.notes,
        )
        db.add(session)
        await db.flush()

        for exercise_data in payload.exercises:
            exercise = WorkoutExercise(
                session_id=session.id,
                name=exercise_data.name,
                sets=exercise_data.sets,
                reps=exercise_data.reps,
                duration_seconds=exercise_data.duration_seconds,
                weight_grams=exercise_data.weight_grams,
                notes=exercise_data.notes,
            )
            db.add(exercise)

        await db.flush()
        logger.info("workout session created session_id=%s plan_id=%s", session.id, payload.plan_id)
        return session

    async def list_sessions(self, db: AsyncSession, family_id: uuid.UUID, plan_id: uuid.UUID) -> list[WorkoutSession]:
        plan = await db.get(WorkoutPlan, plan_id)
        if plan is None:
            raise AppError(code="PLAN_NOT_FOUND", status=404, detail="Workout plan not found.")
        await self._get_member_for_family(db, plan.member_id, family_id)
        result = await db.execute(
            select(WorkoutSession).where(WorkoutSession.plan_id == plan_id).order_by(WorkoutSession.created_at.desc())
        )
        return list(result.scalars().all())


workout_service = WorkoutService()
