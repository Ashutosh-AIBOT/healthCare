from datetime import date

import pytest
from pydantic import ValidationError

from app.services.xomni_service import (
    _extract_action,
    _fallback_fitness_action,
    _hour_to_minute,
    _is_action_confirmation,
    _is_action_rejection,
)
from app.schemas.time import TodoIn


def test_timed_todo_schema_accepts_recurrence() -> None:
    todo = TodoIn(
        title="Walk",
        due_date=date(2026, 9, 9),
        start_minute=840,
        end_minute=960,
        recurrence_rule="weekdays",
        recurrence_until=date(2026, 9, 30),
    )
    assert todo.start_minute == 840
    assert todo.recurrence_rule == "weekdays"


def test_timed_todo_schema_rejects_out_of_range_minutes() -> None:
    with pytest.raises(ValidationError):
        TodoIn(title="Broken", due_date=date(2026, 9, 9), start_minute=900, end_minute=1441)


def test_xomni_confirmation_phrases_are_channel_neutral() -> None:
    assert _is_action_confirmation("Yes, update it")
    assert _is_action_confirmation("confirm")
    assert _is_action_confirmation("go ahead")
    assert _is_action_rejection("No, leave it unchanged")
    assert not _is_action_confirmation("maybe change the time")


def test_xomni_action_contract_supports_update_without_accepting_unknown_ops() -> None:
    text, action = _extract_action(
        'I can change it after you confirm. '
        '{"action":"update_todo","existing_title":"Walking",'
        '"title":"Walking outside","start_hour":14,"end_hour":16}'
    )
    assert "Walking" not in text
    assert action == {
        "action": "update_todo",
        "existing_title": "Walking",
        "title": "Walking outside",
        "start_hour": 14,
        "end_hour": 16,
    }

    unchanged, unsupported = _extract_action(
        'I cannot do that {"action":"run_arbitrary_code","value":"x"}'
    )
    assert unsupported is None
    assert unchanged == 'I cannot do that {"action":"run_arbitrary_code","value":"x"}'


def test_xomni_action_times_support_quarter_hours() -> None:
    assert _hour_to_minute(14) == 840
    assert _hour_to_minute(14.5) == 870
    assert _hour_to_minute(14.25) == 855
    assert _hour_to_minute(14.1) is None


def test_fitness_request_gets_confirmation_gated_fallback_action() -> None:
    action = _fallback_fitness_action("Please log a 30 minute walking activity for today.")
    assert action == {
        "action": "propose_fitness_activity",
        "activity_type": "walking",
        "duration_minutes": 30,
        "logged_date": date.today().isoformat(),
        "notes": "Captured from the user's explicit Xomni activity request.",
    }
    assert _fallback_fitness_action("How many minutes should I walk?") is None
