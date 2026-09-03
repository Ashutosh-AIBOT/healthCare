"""Integration tests for M13 nutrition."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.db.session import set_rls_bypass
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.nutrition import FoodItem, MealType
from app.models.provider import DoctorDetail, ProviderProfile
from app.models.user import User
from app.schemas.nutrition import FoodLogCreate, NutritionPlanCreate, NutritionTargetCreate
from tests.helpers_auth import register_verified


async def _make_verified_doctor(db, *, slug_suffix: str) -> tuple[User, ProviderProfile]:
    doctor_user = User(
        email=f"nutrition-doc-{slug_suffix}-{uuid.uuid4().hex[:8]}@example.com",
        handle=f"nutrition_doc_{slug_suffix}_{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        role="doctor",
        is_verified=True,
    )
    db.add(doctor_user)
    await db.flush()
    profile = ProviderProfile(
        user_id=doctor_user.id,
        provider_type="doctor",
        display_name=f"Dr Nutrition {slug_suffix.title()}",
        slug=f"dr-nutrition-{slug_suffix}-{uuid.uuid4().hex[:6]}",
        verification_status="verified",
        is_active=True,
        consultation_fee_paise=50000,
    )
    db.add(profile)
    await db.flush()
    db.add(DoctorDetail(provider_profile_id=profile.id, specializations="General Medicine"))
    await db.flush()
    return doctor_user, profile


class TestNutrition:
    async def test_patient_can_log_food(self, client, db):
        login = await register_verified(
            client, email="nutrition-patient@example.com", handle="nutrition_patient", full_name="NutritionPatient"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Nutrition Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "male"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        await set_rls_bypass(db, True)
        food = FoodItem(
            name="Oatmeal",
            slug="oatmeal",
            description="Whole grain oats",
            serving_unit="bowl",
            calories_kcal=150,
            protein_g=5,
            carbs_g=27,
            fat_g=3,
            fiber_g=4,
            glycemic_index=55,
            is_verified=1,
        )
        db.add(food)
        await db.flush()
        await set_rls_bypass(db, False)

        log_resp = await client.post(
            "/api/v1/nutrition/log",
            json={
                "member_id": member_id,
                "food_item_id": str(food.id),
                "meal_type": MealType.BREAKFAST,
                "quantity": 1.0,
                "unit": "bowl",
                "calories_kcal": 150,
                "protein_g": 5,
                "carbs_g": 27,
                "fat_g": 3,
                "fiber_g": 4,
                "source": "search",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert log_resp.status_code == 201, log_resp.text
        data = log_resp.json()
        assert data["meal_type"] == MealType.BREAKFAST
        assert data["calories_kcal"] == 150

    async def test_patient_can_set_nutrition_target(self, client, db):
        login = await register_verified(
            client, email="nutrition-target@example.com", handle="nutrition_target", full_name="NutritionTarget"
        )
        token = login.json()["tokens"]["access_token"]

        fam_resp = await client.post(
            "/api/v1/families/",
            json={"name": "Nutrition Target Family"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert fam_resp.status_code == 201

        member_resp = await client.post(
            "/api/v1/families/members",
            json={"relation": "other", "date_of_birth": "1990-01-01", "gender": "female"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert member_resp.status_code == 201, member_resp.text
        member_id = member_resp.json()["id"]

        target_resp = await client.post(
            "/api/v1/nutrition/targets",
            json={
                "member_id": member_id,
                "daily_calories_kcal": 2000,
                "daily_protein_g": 60,
                "daily_carbs_g": 250,
                "daily_fat_g": 65,
                "daily_fiber_g": 25,
                "max_glycemic_index": 55,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert target_resp.status_code == 201, target_resp.text
        data = target_resp.json()
        assert data["daily_calories_kcal"] == 2000
