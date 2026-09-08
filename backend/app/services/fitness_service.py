"""Fitness service — 3-level goals, activity logging, AI food suggestions."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import LLMGateway
from app.models.xomni import FitnessProfile, ActivityLog


LEVEL_DESCRIPTIONS = {
    1: {
        "name": "Beginner",
        "subtitle": "Weight Loss & Foundation",
        "description": "Build healthy habits, burn excess fat, improve stamina. Perfect for those starting their fitness journey.",
        "color": "emerald",
        "recommended_workouts": ["Walking 30 min", "Light yoga", "Bodyweight squats", "Swimming (casual)"],
        "weekly_days": 3,
        "intensity": "Low to moderate",
        "rest_days": 4,
    },
    2: {
        "name": "Intermediate",
        "subtitle": "Muscle Building & Toning",
        "description": "Build lean muscle, improve strength and body composition. For those with 3-6 months of consistent training.",
        "color": "blue",
        "recommended_workouts": ["Weight training 3x/week", "HIIT 2x/week", "Running 5km", "Cycling"],
        "weekly_days": 4,
        "intensity": "Moderate to high",
        "rest_days": 3,
    },
    3: {
        "name": "Advanced",
        "subtitle": "Athletic Performance",
        "description": "Peak performance, sport-specific training, maximize VO2max and strength. For dedicated athletes.",
        "color": "purple",
        "recommended_workouts": ["Heavy compound lifts", "Sprint intervals", "Sport training", "CrossFit"],
        "weekly_days": 5,
        "intensity": "High",
        "rest_days": 2,
    },
}

GOAL_TYPES = [
    "weight_loss",
    "muscle_build",
    "endurance",
    "general_fitness",
    "athletic",
]

ACTIVITY_CALORIES_PER_MINUTE = {
    "running": 10,
    "cycling": 8,
    "swimming": 7,
    "strength": 6,
    "yoga": 3,
    "walking": 4,
    "hiit": 12,
    "dancing": 5,
    "other": 5,
}


async def get_or_create_fitness_profile(
    db: AsyncSession, *, user_id: uuid.UUID
) -> FitnessProfile:
    q = select(FitnessProfile).where(FitnessProfile.user_id == user_id)
    profile = (await db.execute(q)).scalars().first()
    if profile is None:
        profile = FitnessProfile(user_id=user_id, level=1, goal_type="general_fitness")
        db.add(profile)
        await db.flush()
    return profile


async def update_fitness_profile(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    level: int | None = None,
    goal_type: str | None = None,
    target_weight_kg: float | None = None,
    target_body_fat_pct: float | None = None,
    target_date: date | None = None,
    weekly_workout_days: int | None = None,
) -> dict[str, Any]:
    profile = await get_or_create_fitness_profile(db, user_id=user_id)
    if level is not None:
        profile.level = max(1, min(3, level))
    if goal_type is not None:
        profile.goal_type = goal_type
    if target_weight_kg is not None:
        profile.target_weight_kg = target_weight_kg
    if target_body_fat_pct is not None:
        profile.target_body_fat_pct = target_body_fat_pct
    if target_date is not None:
        profile.target_date = target_date
    if weekly_workout_days is not None:
        profile.weekly_workout_days = max(1, min(7, weekly_workout_days))
    await db.flush()
    return _profile_to_dict(profile)


def _profile_to_dict(profile: FitnessProfile) -> dict[str, Any]:
    level_info = LEVEL_DESCRIPTIONS.get(profile.level, LEVEL_DESCRIPTIONS[1])
    return {
        "id": str(profile.id),
        "level": profile.level,
        "level_info": level_info,
        "goal_type": profile.goal_type,
        "target_weight_kg": profile.target_weight_kg,
        "target_body_fat_pct": profile.target_body_fat_pct,
        "target_date": str(profile.target_date) if profile.target_date else None,
        "weekly_workout_days": profile.weekly_workout_days,
    }


async def log_activity(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    activity_type: str,
    duration_minutes: int,
    calories_burned: int | None = None,
    distance_km: float | None = None,
    notes: str | None = None,
    logged_date: date | None = None,
) -> dict[str, Any]:
    if logged_date is None:
        logged_date = date.today()

    # Auto-calculate calories if not provided
    if calories_burned is None:
        cal_per_min = ACTIVITY_CALORIES_PER_MINUTE.get(activity_type.lower(), 5)
        calories_burned = cal_per_min * duration_minutes

    log = ActivityLog(
        user_id=user_id,
        activity_type=activity_type,
        duration_minutes=duration_minutes,
        calories_burned=calories_burned,
        distance_km=distance_km,
        notes=notes,
        logged_date=logged_date,
    )
    db.add(log)
    await db.flush()
    return {
        "id": str(log.id),
        "activity_type": log.activity_type,
        "duration_minutes": log.duration_minutes,
        "calories_burned": log.calories_burned,
        "distance_km": log.distance_km,
        "logged_date": str(log.logged_date),
    }


async def get_activities(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    days: int = 7,
) -> dict[str, Any]:
    since = date.today() - timedelta(days=days)
    q = (
        select(ActivityLog)
        .where(ActivityLog.user_id == user_id, ActivityLog.logged_date >= since)
        .order_by(ActivityLog.logged_date.desc())
    )
    logs = list((await db.execute(q)).scalars().all())

    # Build week chart
    week_data = []
    for i in range(days - 1, -1, -1):
        day = date.today() - timedelta(days=i)
        day_logs = [l for l in logs if l.logged_date == day]
        total_mins = sum(l.duration_minutes for l in day_logs)
        total_cal = sum(l.calories_burned or 0 for l in day_logs)
        week_data.append({
            "date": str(day),
            "day": day.strftime("%a"),
            "minutes": total_mins,
            "calories": total_cal,
            "active": total_mins > 0,
        })

    total_minutes = sum(l.duration_minutes for l in logs)
    active_days = len({l.logged_date for l in logs})

    return {
        "logs": [
            {
                "id": str(l.id),
                "activity_type": l.activity_type,
                "duration_minutes": l.duration_minutes,
                "calories_burned": l.calories_burned,
                "distance_km": l.distance_km,
                "logged_date": str(l.logged_date),
            }
            for l in logs
        ],
        "week_chart": week_data,
        "summary": {
            "total_minutes": total_minutes,
            "active_days": active_days,
            "avg_daily_minutes": round(total_minutes / days, 1),
        },
    }


async def get_ai_food_suggestions(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> str:
    """Get AI food suggestions based on fitness level and nutrition profile."""
    profile = await get_or_create_fitness_profile(db, user_id=user_id)

    # Get nutrition profile if exists
    from app.models.xomni import NutritionProfile
    nq = select(NutritionProfile).where(NutritionProfile.user_id == user_id)
    nutrition = (await db.execute(nq)).scalars().first()

    level_info = LEVEL_DESCRIPTIONS.get(profile.level, LEVEL_DESCRIPTIONS[1])

    nutrition_ctx = ""
    if nutrition:
        nutrition_ctx = f"""
- Diet type: {nutrition.diet_type}
- Daily protein target: {nutrition.target_protein_g}g
- Daily calories: {nutrition.tdee_calories}
- Goal: {nutrition.goal}
"""

    prompt = f"""Suggest a practical food plan for a {level_info['name']} level fitness person.

Fitness profile:
- Level: {profile.level} ({level_info['name']} - {level_info['subtitle']})
- Goal: {profile.goal_type}
- Training: {level_info['intensity']} intensity, {profile.weekly_workout_days} days/week
{nutrition_ctx}

Provide:
1. Pre-workout foods (30-60 min before training)
2. Post-workout foods (within 2 hours)
3. Top 5 foods for this fitness goal
4. Foods to avoid
5. Hydration guide

Keep suggestions practical and use Indian food context. Be specific with quantities."""

    gateway = LLMGateway(db, user_id=str(user_id))
    try:
        result = await gateway.complete(prompt=prompt)
        return result.text
    except Exception as e:
        return f"Unable to generate suggestions. Error: {str(e)}"
