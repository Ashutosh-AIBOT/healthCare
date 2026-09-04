"""Pydantic schemas for Module 4 Dashboard."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.dashboard import DEFAULT_WIDGET_VISIBILITY, WIDGET_KEYS


class DashboardSummary(BaseModel):
    user_id: str
    composite_score: float = Field(..., ge=0.0, le=100.0)
    time_management_score: float = Field(..., ge=0.0, le=100.0)
    diet_score: float = Field(..., ge=0.0, le=100.0)
    fitness_score: float = Field(..., ge=0.0, le=100.0)
    widget_visibility: dict[str, bool]
    chatbot_toggle_state: bool
    last_recomputed_at: datetime | None


class DashboardPreferences(BaseModel):
    widget_visibility: dict[str, bool] = Field(default_factory=dict)
    chatbot_toggle_state: bool | None = None

    @classmethod
    def normalize_widgets(cls, payload: dict[str, bool]) -> dict[str, bool]:
        out = dict(DEFAULT_WIDGET_VISIBILITY)
        for key in WIDGET_KEYS:
            if key in payload:
                out[key] = bool(payload[key])
        return out
