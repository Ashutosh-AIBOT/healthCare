"""Deterministic red-flag triage floor — MUST run before any model / RAG call."""

from __future__ import annotations

from dataclasses import dataclass

# India-focused emergency + mental-health helplines (no PHI).
HELPLINE_TEXT = (
    "Emergency: 112 · Ambulance: 108 · Mental health (Tele MANAS): 14416 · "
    "AASRA suicide prevention: 9820466726"
)

EMERGENCY_BANNER = (
    "What you have described may need urgent medical attention. "
    "Please contact emergency services or go to the nearest emergency department now. "
    "Aarogya cannot assess emergencies."
)

# Keyword / phrase rules — bias toward false positives; recall is the gate.
_RED_FLAG_RULES: tuple[tuple[str, str], ...] = (
    ("chest_pain", "chest pain"),
    ("chest_pain", "crushing chest"),
    ("breathlessness", "can't breathe"),
    ("breathlessness", "cannot breathe"),
    ("breathlessness", "shortness of breath"),
    ("breathlessness", "breathlessness"),
    ("breathlessness", "difficulty breathing"),
    ("stroke", "face drooping"),
    ("stroke", "arm weakness"),
    ("stroke", "slurred speech"),
    ("stroke", "stroke"),
    ("anaphylaxis", "anaphylaxis"),
    ("anaphylaxis", "throat closing"),
    ("anaphylaxis", "severe allergic"),
    ("suicidal", "suicidal"),
    ("suicidal", "kill myself"),
    ("suicidal", "want to die"),
    ("suicidal", "end my life"),
    ("suicidal", "suicide"),
    ("infant_fever", "infant fever"),
    ("infant_fever", "baby has fever"),
    ("obstetric", "obstetric bleeding"),
    ("obstetric", "bleeding in pregnancy"),
    ("obstetric", "pregnant and bleeding"),
    ("unconscious", "unconscious"),
    ("unconscious", "passed out"),
    ("seizure", "seizure"),
    ("seizure", "convulsion"),
    ("heart_attack", "heart attack"),
    ("heart_attack", "cardiac arrest"),
)


@dataclass(frozen=True)
class TriageVerdict:
    flagged: bool
    matched_rule: str | None = None


def screen(text: str) -> TriageVerdict:
    """Rule pass only — no network, <50ms. Never log the message body."""
    lowered = (text or "").lower()
    for rule_id, phrase in _RED_FLAG_RULES:
        if phrase in lowered:
            return TriageVerdict(flagged=True, matched_rule=rule_id)
    return TriageVerdict(flagged=False)


def is_red_flag(text: str) -> bool:
    return screen(text).flagged


def emergency_response(*, locale: str = "en") -> str:
    """Pre-written short-circuit; helplines always included."""
    _ = locale  # locale-specific copy later
    return f"{EMERGENCY_BANNER}\n\nHelplines: {HELPLINE_TEXT}"
