"""P0 characterization + P1/P2 tests for Xomni context assembly (no DB required).

P0 pins current behavior so refactors cannot silently change it:
- mode prompts contain their canonical action shapes
- action extraction strips the JSON block from visible text
- guardrails always append the medical disclaimer
- triage flags emergencies before anything else
"""

import os

import asyncio
import uuid

import pytest

from app.ai import guardrails, triage
from app.services import xomni_service
from app.services.xomni_service import (
    _extract_action,
    _get_mode_system_prompt,
    context_assembly_enabled,
)


# ── P0: current behavior pins ────────────────────────────────────────────


def test_food_prompt_requires_canonical_meal_action() -> None:
    prompt = _get_mode_system_prompt("food")
    assert "propose_meal_plan" in prompt
    assert '"action"' in prompt


def test_timetable_prompt_requires_canonical_todo_action() -> None:
    prompt = _get_mode_system_prompt("timetable")
    assert "propose_todo" in prompt


def test_fitness_prompt_requires_canonical_activity_action() -> None:
    prompt = _get_mode_system_prompt("fitness")
    assert "propose_fitness_activity" in prompt


def test_extract_action_keeps_visible_text_clean() -> None:
    clean, action = _extract_action('Plan: {"action": "propose_todo", "title": "Walk"} done')
    assert action is not None and action["title"] == "Walk"
    assert "propose_todo" not in clean


def test_guardrails_always_append_disclaimer() -> None:
    out = guardrails.apply_guardrails("Eat more fibre.")
    assert guardrails.get_medical_disclaimer() in out


def test_triage_flags_emergency_phrasing() -> None:
    assert triage.screen("I have crushing chest pain").flagged
    assert not triage.screen("What should I eat for lunch?").flagged


def test_context_assembly_flag_respects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XOMNI_CONTEXT_ASSEMBLY", "false")
    assert context_assembly_enabled() is False
    monkeypatch.setenv("XOMNI_CONTEXT_ASSEMBLY", "true")
    assert context_assembly_enabled() is True


def test_context_assembly_flag_defaults_off_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XOMNI_CONTEXT_ASSEMBLY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    assert context_assembly_enabled() is False
    monkeypatch.setenv("APP_ENV", "development")
    assert context_assembly_enabled() is True


# ── P1: summarizers ──────────────────────────────────────────────────────

from app.services.xomni_service import (  # noqa: E402
    summarize_activities,
    summarize_checkup_catalog,
    summarize_lab_values,
    summarize_meal_plan,
    summarize_nutrition_profile,
    summarize_todos,
)


def test_nutrition_summarizer_with_profile() -> None:
    text = summarize_nutrition_profile({
        "bmi": 24.2, "goal": "maintain", "diet_type": "veg",
        "tdee_calories": 1950, "target_protein_g": 90,
        "target_carbs_g": 250, "target_fat_g": 55,
    })
    assert "1950" in text and "90" in text


def test_nutrition_summarizer_without_profile() -> None:
    assert "unknown" in summarize_nutrition_profile(None).lower()


def test_meal_plan_summarizer() -> None:
    text = summarize_meal_plan({"lunch": [{"name": "Dal", "calories": 180}], "dinner": []})
    assert "Dal" in text


def test_meal_plan_summarizer_empty() -> None:
    assert "unknown" in summarize_meal_plan({}).lower()
    assert "unknown" in summarize_meal_plan(None).lower()


def test_activities_summarizer() -> None:
    text = summarize_activities([
        {"activity_type": "walking", "duration_minutes": 30, "logged_date": "2026-09-09"},
        {"activity_type": "yoga", "duration_minutes": 20, "logged_date": "2026-09-10"},
    ])
    assert "50" in text and "walking" in text


def test_activities_summarizer_empty() -> None:
    assert "unknown" in summarize_activities([]).lower()


def test_todos_summarizer() -> None:
    text = summarize_todos([{"title": "Evening Walk", "priority": "normal"}])
    assert "Evening Walk" in text
    assert "unknown" in summarize_todos([]).lower()


def test_lab_values_summarize_only_no_exact_numbers() -> None:
    """Reports privacy rule: flags + counts, never numeric values."""
    text = summarize_lab_values([
        {"analyte_name": "Hemoglobin", "value_num": 13.2, "unit": "g/dL",
         "flag": "within_range", "page": 1},
        {"analyte_name": "Glucose", "value_num": 210.0, "unit": "mg/dL",
         "flag": "high", "page": 1},
    ])
    assert "Glucose" in text and "high" in text.lower()
    assert "210" not in text and "13.2" not in text


def test_lab_values_empty() -> None:
    assert "unknown" in summarize_lab_values([]).lower()


def test_checkup_catalog_summarizer() -> None:
    text = summarize_checkup_catalog([
        {"name": "HbA1c", "what_it_checks": "avg blood sugar",
         "prep_note": "No fasting", "fasting_required": False},
    ])
    assert "HbA1c" in text and "fasting" in text.lower()
    # No catalog matches: omit the section entirely (no "unknown" noise).
    assert summarize_checkup_catalog([]) == ""
    assert summarize_checkup_catalog(None) == ""


def test_summarizers_never_raise_on_junk() -> None:
    assert isinstance(summarize_nutrition_profile({"bmi": object()}), str)
    assert isinstance(summarize_meal_plan({"lunch": "not-a-list"}), str)
    assert isinstance(summarize_lab_values([None, "x"]), str)


def test_module_exports_summarizers() -> None:
    for name in (
        "summarize_nutrition_profile", "summarize_meal_plan", "summarize_activities",
        "summarize_todos", "summarize_lab_values", "summarize_checkup_catalog",
    ):
        assert callable(getattr(xomni_service, name)), name


# ── P2: assembly flag-off never touches the DB ───────────────────────────


def test_assembly_flag_off_returns_empty_without_db(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XOMNI_CONTEXT_ASSEMBLY", "false")
    block, cites = asyncio.run(
        xomni_service._assemble_user_context(
            None, user_id=uuid.uuid4(), mode="food", message="hi"  # type: ignore[arg-type]
        )
    )
    assert block == "" and cites == []
