"""Nutrition service — BMI calculation (Mifflin-St Jeor), macro targets, AI meal plans."""

from __future__ import annotations

import math
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import LLMGateway
from app.models.xomni import NutritionProfile, MealPlan


ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "extra_active": 1.9,
}

GOAL_CALORIE_ADJUSTMENT = {
    "lose_weight": -500,
    "maintain": 0,
    "gain_muscle": +300,
}

# Required micronutrients per day (adult average, with gender variants noted)
MICRONUTRIENTS = {
    "Protein": {"unit": "g", "male": 56, "female": 46, "note": "increases with activity"},
    "Calcium": {"unit": "mg", "male": 1000, "female": 1000, "note": "1200mg for 50+ women"},
    "Iron": {"unit": "mg", "male": 8, "female": 18, "note": "8mg for men, 18mg for pre-menopausal women"},
    "Vitamin D": {"unit": "IU", "male": 600, "female": 600, "note": "800 IU for 70+"},
    "Vitamin B12": {"unit": "mcg", "male": 2.4, "female": 2.4, "note": "especially important for vegans"},
    "Omega-3 (ALA)": {"unit": "g", "male": 1.6, "female": 1.1, "note": "EPA+DHA separately needed"},
    "Fiber": {"unit": "g", "male": 38, "female": 25, "note": "reduces with age after 50"},
    "Potassium": {"unit": "mg", "male": 3400, "female": 2600, "note": "from fruits and vegetables"},
    "Magnesium": {"unit": "mg", "male": 420, "female": 320, "note": "important for muscle function"},
    "Zinc": {"unit": "mg", "male": 11, "female": 8, "note": "higher for athletes"},
    "Vitamin C": {"unit": "mg", "male": 90, "female": 75, "note": "higher for smokers"},
    "Folate": {"unit": "mcg", "male": 400, "female": 400, "note": "600mcg during pregnancy"},
}

VEG_PROTEIN_SOURCES = [
    {"food": "Paneer (100g)", "protein_g": 18, "calories": 265},
    {"food": "Tofu (100g)", "protein_g": 8, "calories": 76},
    {"food": "Lentils / Dal (100g cooked)", "protein_g": 9, "calories": 116},
    {"food": "Chickpeas (100g cooked)", "protein_g": 15, "calories": 164},
    {"food": "Greek Yogurt (100g)", "protein_g": 10, "calories": 59},
    {"food": "Quinoa (100g cooked)", "protein_g": 4, "calories": 120},
    {"food": "Pumpkin Seeds (30g)", "protein_g": 9, "calories": 170},
    {"food": "Almonds (30g)", "protein_g": 6, "calories": 174},
    {"food": "Kidney Beans (100g cooked)", "protein_g": 9, "calories": 127},
    {"food": "Soy Milk (240ml)", "protein_g": 8, "calories": 105},
]

NON_VEG_PROTEIN_SOURCES = [
    {"food": "Chicken Breast (100g)", "protein_g": 31, "calories": 165},
    {"food": "Eggs (2 large)", "protein_g": 13, "calories": 143},
    {"food": "Salmon (100g)", "protein_g": 25, "calories": 208},
    {"food": "Tuna (100g)", "protein_g": 30, "calories": 132},
    {"food": "Mutton (100g)", "protein_g": 25, "calories": 294},
    {"food": "Prawns (100g)", "protein_g": 24, "calories": 99},
    {"food": "Cottage Cheese (100g)", "protein_g": 11, "calories": 98},
    {"food": "Turkey (100g)", "protein_g": 29, "calories": 189},
]


def calculate_bmi(weight_kg: float, height_cm: float) -> float:
    """Standard BMI formula."""
    height_m = height_cm / 100
    return round(weight_kg / (height_m ** 2), 1)


def bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25.0:
        return "Normal weight"
    elif bmi < 30.0:
        return "Overweight"
    else:
        return "Obese"


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> int:
    """Mifflin-St Jeor BMR formula."""
    if gender == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return round(bmr)


def calculate_tdee(bmr: int, activity_level: str) -> int:
    """Total Daily Energy Expenditure."""
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return round(bmr * multiplier)


def calculate_macros(tdee: int, goal: str, weight_kg: float) -> dict[str, int]:
    """Calculate macro targets in grams."""
    adjusted_calories = tdee + GOAL_CALORIE_ADJUSTMENT.get(goal, 0)
    adjusted_calories = max(1200, adjusted_calories)  # safety floor

    # Protein: 1.6-2.2g per kg for muscle, 1.2-1.6g for weight loss
    if goal == "gain_muscle":
        protein_g = round(weight_kg * 2.0)
    elif goal == "lose_weight":
        protein_g = round(weight_kg * 1.6)
    else:
        protein_g = round(weight_kg * 1.4)

    protein_calories = protein_g * 4
    remaining = adjusted_calories - protein_calories

    # Fat: 25-35% of calories
    fat_calories = round(adjusted_calories * 0.28)
    fat_g = round(fat_calories / 9)

    # Carbs: remaining
    carb_calories = remaining - fat_calories
    carb_g = round(max(carb_calories, 0) / 4)

    return {
        "target_calories": adjusted_calories,
        "protein_g": protein_g,
        "carbs_g": carb_g,
        "fat_g": fat_g,
    }


def get_micronutrient_requirements(gender: str, age: int) -> list[dict]:
    """Get personalized micronutrient requirements."""
    result = []
    for name, data in MICRONUTRIENTS.items():
        amount = data.get("male" if gender == "male" else "female", 0)
        # Age adjustments
        if name == "Calcium" and age >= 50 and gender == "female":
            amount = 1200
        result.append({
            "nutrient": name,
            "required": amount,
            "unit": data["unit"],
            "note": data.get("note", ""),
        })
    return result


def get_protein_sources(diet_type: str) -> list[dict]:
    """Get protein-rich food suggestions based on diet type."""
    if diet_type in ("veg", "vegan"):
        return VEG_PROTEIN_SOURCES
    elif diet_type == "eggetarian":
        # Veg + eggs
        eggs = [s for s in NON_VEG_PROTEIN_SOURCES if "egg" in s["food"].lower()]
        return VEG_PROTEIN_SOURCES + eggs
    else:
        return VEG_PROTEIN_SOURCES + NON_VEG_PROTEIN_SOURCES


def ideal_weight_range(height_cm: float, gender: str) -> dict[str, float]:
    """BMI 18.5-24.9 weight range for this height."""
    h_m = height_cm / 100
    low = round(18.5 * h_m * h_m, 1)
    high = round(24.9 * h_m * h_m, 1)
    return {"min_kg": low, "max_kg": high}


async def calculate_and_save_profile(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    height_cm: float,
    weight_kg: float,
    age: int,
    gender: str,
    activity_level: str,
    goal: str,
    diet_type: str,
    user_restrictions: str | None = None,
) -> dict[str, Any]:
    """Calculate BMI + macros, upsert NutritionProfile, return full result."""
    bmi = calculate_bmi(weight_kg, height_cm)
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    tdee = calculate_tdee(bmr, activity_level)
    macros = calculate_macros(tdee, goal, weight_kg)
    micronutrients = get_micronutrient_requirements(gender, age)
    protein_sources = get_protein_sources(diet_type)
    ideal = ideal_weight_range(height_cm, gender)

    # Upsert profile
    q = select(NutritionProfile).where(NutritionProfile.user_id == user_id)
    profile = (await db.execute(q)).scalars().first()
    if profile is None:
        profile = NutritionProfile(user_id=user_id)
        db.add(profile)

    profile.height_cm = height_cm
    profile.weight_kg = weight_kg
    profile.age = age
    profile.gender = gender
    profile.activity_level = activity_level
    profile.goal = goal
    profile.diet_type = diet_type
    profile.bmi = bmi
    profile.bmr_calories = bmr
    profile.tdee_calories = tdee
    profile.target_protein_g = macros["protein_g"]
    profile.target_carbs_g = macros["carbs_g"]
    profile.target_fat_g = macros["fat_g"]
    if user_restrictions is not None:
        profile.user_restrictions = user_restrictions

    await db.flush()

    return {
        "profile_id": str(profile.id),
        "bmi": bmi,
        "bmi_category": bmi_category(bmi),
        "ideal_weight_kg": ideal,
        "bmr_calories": bmr,
        "tdee_calories": tdee,
        "macros": macros,
        "micronutrients": micronutrients,
        "protein_sources": protein_sources[:8],
        "diet_type": diet_type,
        "goal": goal,
    }


async def generate_meal_plan(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    profile: NutritionProfile | None = None,
    user_restrictions: str | None = None,
) -> dict[str, Any]:
    """Generate AI-powered meal plan based on nutrition profile."""
    if profile is None:
        q = select(NutritionProfile).where(NutritionProfile.user_id == user_id)
        profile = (await db.execute(q)).scalars().first()

    if profile is None:
        return {"error": "Please complete your nutrition profile first."}

    restrictions_text = ""
    if user_restrictions or profile.user_restrictions:
        restrictions_text = f"Dietary restrictions/dislikes: {user_restrictions or profile.user_restrictions}"

    prompt = f"""Create a detailed daily meal plan for a person with these requirements:

Goal: {profile.goal}
Diet type: {profile.diet_type} (veg/non-veg/vegan)
Daily calories: {profile.tdee_calories} kcal
Protein target: {profile.target_protein_g}g
Carbs target: {profile.target_carbs_g}g  
Fat target: {profile.target_fat_g}g
{restrictions_text}

Create a practical Indian meal plan with exact quantities. Include:
1. Early morning (6-7am): Something light
2. Breakfast (8-9am): Filling and nutritious
3. Mid-morning snack (11am): Optional
4. Lunch (1-2pm): Main meal
5. Evening snack (4-5pm): Healthy option
6. Dinner (7-8pm): Light but complete
7. Recommended fruits (list 3-4 daily fruits with quantities)
8. Foods to avoid/limit

For each meal, specify: food items, quantity, approximate protein/calories.
Keep suggestions practical, affordable, and use commonly available Indian ingredients.
Format as a structured list."""

    gateway = LLMGateway(db, user_id=str(user_id))
    try:
        result = await gateway.complete(prompt=prompt)
        plan_text = result.text
    except Exception as e:
        plan_text = f"Unable to generate plan: {str(e)}"

    # Save the plan
    meal_plan = MealPlan(
        user_id=user_id,
        profile_id=profile.id,
        plan_json={"text": plan_text, "generated_at": str(__import__('datetime').datetime.utcnow())},
        ai_generated=True,
    )
    db.add(meal_plan)
    await db.flush()

    return {
        "plan_id": str(meal_plan.id),
        "plan_text": plan_text,
        "macros": {
            "calories": profile.tdee_calories,
            "protein_g": profile.target_protein_g,
            "carbs_g": profile.target_carbs_g,
            "fat_g": profile.target_fat_g,
        },
    }


async def get_nutrition_profile(db: AsyncSession, *, user_id: uuid.UUID) -> dict | None:
    """Get user's saved nutrition profile."""
    q = select(NutritionProfile).where(NutritionProfile.user_id == user_id)
    profile = (await db.execute(q)).scalars().first()
    if not profile:
        return None
    return {
        "id": str(profile.id),
        "height_cm": profile.height_cm,
        "weight_kg": profile.weight_kg,
        "age": profile.age,
        "gender": profile.gender,
        "activity_level": profile.activity_level,
        "goal": profile.goal,
        "diet_type": profile.diet_type,
        "bmi": profile.bmi,
        "bmr_calories": profile.bmr_calories,
        "tdee_calories": profile.tdee_calories,
        "target_protein_g": profile.target_protein_g,
        "target_carbs_g": profile.target_carbs_g,
        "target_fat_g": profile.target_fat_g,
        "user_restrictions": profile.user_restrictions,
    }
