"""Unit tests for Xomni dashboard-action shapes (no DB required)."""

import pytest

from app.services.xomni_service import (
    _extract_action,
    _normalize_fitness_action,
    _normalize_meal_buckets,
    _normalize_meal_items,
    _normalize_personal_context,
    _normalize_todo_action,
)


def test_extract_action_strips_block_from_text() -> None:
    answer = 'Here is your plan {"action": "propose_todo", "title": "Walk"} enjoy!'
    clean, action = _extract_action(answer)
    assert action == {"action": "propose_todo", "title": "Walk"}
    assert "propose_todo" not in clean
    assert "enjoy" in clean


def test_extract_action_ignores_non_action_json() -> None:
    clean, action = _extract_action('Data {"foo": 1} and more text')
    assert action is None
    assert "foo" in clean


def test_meal_items_canonical_shape() -> None:
    items = _normalize_meal_items([
        {"name": "Dal", "calories": 180, "protein": 12, "carbs": 20, "fats": 4},
    ])
    assert items == [{"name": "Dal", "calories": 180.0, "protein": 12.0, "carbs": 20.0, "fats": 4.0}]


def test_meal_items_accept_aliases() -> None:
    items = _normalize_meal_items([
        {"description": "Oats", "kcal": 300, "protein_g": 12, "carbs_g": 40, "fat_g": 10},
    ])
    assert items[0]["name"] == "Oats"
    assert items[0]["calories"] == 300.0
    assert items[0]["protein"] == 12.0


def test_meal_items_reject_nameless() -> None:
    with pytest.raises(ValueError):
        _normalize_meal_items([{"calories": 100}])


def test_meal_buckets_canonical() -> None:
    buckets = _normalize_meal_buckets({
        "action": "propose_meal_plan",
        "meal_type": "lunch",
        "proposal": [{"name": "Roti", "calories": 180, "protein": 6, "carbs": 30, "fats": 2}],
    })
    assert set(buckets) == {"lunch"}
    assert buckets["lunch"][0]["name"] == "Roti"


def test_meal_buckets_legacy_meals_shape() -> None:
    buckets = _normalize_meal_buckets({
        "action": "propose_meal_plan",
        "meals": [
            {"name": "Upma", "meal": "breakfast", "calories": 300, "protein": 12, "carbs": 40, "fats": 10},
            {"name": "Dal", "time": "13:00", "calories": 180, "protein": 12, "carbs": 20, "fats": 4},
        ],
    })
    assert buckets["breakfast"][0]["name"] == "Upma"
    assert buckets["lunch"][0]["name"] == "Dal"


def test_meal_buckets_reject_empty() -> None:
    with pytest.raises(ValueError):
        _normalize_meal_buckets({"action": "propose_meal_plan"})


def test_todo_normalization_defaults() -> None:
    out = _normalize_todo_action({"action": "propose_todo", "title": "  Walk  ", "priority": "bogus"})
    assert out["title"] == "Walk"
    assert out["priority"] == "normal"
    assert out["recurrence_rule"] == "once"


def test_todo_rejects_missing_title() -> None:
    with pytest.raises(ValueError):
        _normalize_todo_action({"action": "propose_todo", "title": "  "})


def test_fitness_normalization() -> None:
    out = _normalize_fitness_action(
        {"action": "propose_fitness_activity", "activity_type": "walking", "duration_minutes": 30}
    )
    assert out["duration_minutes"] == 30


def test_fitness_rejects_bad_duration() -> None:
    with pytest.raises(ValueError):
        _normalize_fitness_action(
            {"action": "propose_fitness_activity", "activity_type": "x", "duration_minutes": 0}
        )


def test_personal_context_allowlist() -> None:
    out = _normalize_personal_context({"goals": ["maintain weight"], "likes": "paneer"})
    assert out["goals"] == ["maintain weight"]
    assert out["likes"] == ["paneer"]


def test_personal_context_rejects_unknown_field() -> None:
    with pytest.raises(ValueError):
        _normalize_personal_context({"diagnosis": ["diabetes"]})


def test_personal_context_rejects_empty() -> None:
    with pytest.raises(ValueError):
        _normalize_personal_context({})
