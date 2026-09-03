"""Output guardrails — strip diagnosis language; append medical disclaimer."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_FALLBACK_DISCLAIMER = (
    "Not a medical device. Aarogya explains and coordinates care — "
    "it does not diagnose, prescribe, or replace a clinician."
)

_DIAGNOSIS_PATTERNS = (
    re.compile(r"\byou have\b.{0,40}\b(disease|cancer|diabetes|infection|disorder)\b", re.I),
    re.compile(r"\bdiagnos(e|is|ed|ing)\b", re.I),
    re.compile(r"\bthis (means|indicates|confirms) you\b", re.I),
    re.compile(r"\byou (definitely|certainly) have\b", re.I),
    re.compile(r"\bprescrib(e|ed|ing)\b", re.I),
    re.compile(r"\btake \d+\s*(mg|mcg|ml|tablet|tablets|capsule)s?\b", re.I),
    re.compile(r"\bprognosis\b", re.I),
    re.compile(r"\btreatment plan\b", re.I),
)


@lru_cache(maxsize=1)
def get_medical_disclaimer() -> str:
    """Prefer verbatim copy-guide disclaimer.ai_output when the file is present."""
    candidates = [
        Path(__file__).resolve().parents[4] / "docs" / "copy-guide.md",
        Path(__file__).resolve().parents[5] / "docs" / "copy-guide.md",
        Path("/app/docs/copy-guide.md"),
    ]
    for path in candidates:
        try:
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            marker = "**`disclaimer.ai_output`**"
            idx = text.find(marker)
            if idx < 0:
                continue
            # Next blockquote line after the marker
            after = text[idx:]
            for line in after.splitlines():
                stripped = line.strip()
                if stripped.startswith(">"):
                    return stripped.lstrip("> ").strip()
        except OSError:
            continue
    return _FALLBACK_DISCLAIMER


MEDICAL_DISCLAIMER = get_medical_disclaimer()


def strip_diagnosis_language(text: str) -> str:
    """Remove or soften diagnostic / dosage phrasing for skeleton enforcement."""
    out = text
    replacements = (
        (re.compile(r"\byou have\b", re.I), "your report shows values related to"),
        (re.compile(r"\bdiagnos(?:e|is|ed|ing)\b", re.I), "explain"),
        (re.compile(r"\bprescrib(?:e|ed|ing)\b", re.I), "discuss with a clinician"),
        (re.compile(r"\bprognosis\b", re.I), "outlook discussion with a clinician"),
        (re.compile(r"\btreatment plan\b", re.I), "topics to discuss with a clinician"),
    )
    for pattern, repl in replacements:
        out = pattern.sub(repl, out)
    # Drop lines that still look like hard diagnosis after soft replace
    kept: list[str] = []
    for line in out.splitlines():
        if any(p.search(line) for p in _DIAGNOSIS_PATTERNS):
            continue
        kept.append(line)
    return "\n".join(kept).strip() or (
        "I can explain values found in your report. Please discuss results with a qualified doctor."
    )


def apply_guardrails(text: str) -> str:
    """Strip unsafe language and append the approved disclaimer."""
    cleaned = strip_diagnosis_language(text)
    disclaimer = get_medical_disclaimer()
    if disclaimer not in cleaned:
        cleaned = f"{cleaned}\n\n{disclaimer}"
    return cleaned
