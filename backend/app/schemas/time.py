from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field


class TimeBlockIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    start_minute: int = Field(ge=0, le=1439)
    end_minute: int = Field(ge=1, le=1440)
    priority: str = Field(default="normal", pattern="^(normal|important|less)$")
    description: str | None = None


class TimeBlockPatch(BaseModel):
    title: str | None = Field(default=None, max_length=120)
    start_minute: int | None = Field(default=None, ge=0, le=1439)
    end_minute: int | None = Field(default=None, ge=1, le=1440)
    priority: str | None = Field(default=None, pattern="^(normal|important|less)$")
    description: str | None = None


class TimeBlockOut(BaseModel):
    id: uuid.UUID
    timetable_id: uuid.UUID
    title: str
    start_minute: int
    end_minute: int
    priority: str
    description: str | None

    model_config = {"from_attributes": True}


class TimeTimetableOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    is_default: bool
    blocks: list[TimeBlockOut]

    model_config = {"from_attributes": True}


class TodoIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    due_date: date
    priority: str = Field(default="normal", pattern="^(normal|important|less)$")
    timetable_block_id: uuid.UUID | None = None


class TodoPatch(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    due_date: date | None = None
    status: str | None = Field(default=None, pattern="^(pending|done)$")
    priority: str | None = Field(default=None, pattern="^(normal|important|less)$")
    timetable_block_id: uuid.UUID | None = None


class TodoOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    due_date: date
    status: str
    priority: str
    timetable_block_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class HolidayRulesIn(BaseModel):
    weekly_weekday: int | None = Field(default=None, ge=0, le=6, description="0=Sunday")
    specific_dates: list[date] = Field(default_factory=list)


class HolidayRuleOut(BaseModel):
    id: uuid.UUID
    rule_type: str
    weekday: int | None
    specific_date: date | None

    model_config = {"from_attributes": True}


class DayBlockStatusIn(BaseModel):
    block_id: uuid.UUID
    status: str = Field(pattern="^(done|partial|skipped)$")


class DayBlockStatusOut(BaseModel):
    id: uuid.UUID
    date: date
    block_id: uuid.UUID
    status: str

    model_config = {"from_attributes": True}


class TimeEntryIn(BaseModel):
    block_id: uuid.UUID
    actual_title: str = Field(min_length=1, max_length=200)
    matched: bool = False
    duration_minutes: int = Field(default=0, ge=0)


class TimeEntryOut(BaseModel):
    id: uuid.UUID
    date: date
    block_id: uuid.UUID
    actual_title: str
    matched: bool
    duration_minutes: int

    model_config = {"from_attributes": True}


class DayPlanBlockOut(BaseModel):
    id: str
    title: str
    start_minute: int
    end_minute: int
    priority: str
    status: str | None = None
    is_current: bool = False
    is_past: bool = False
    needs_checkin: bool = False


class DayPlanOut(BaseModel):
    date: str
    kind: str
    timetable_name: str
    current_minute: int
    blocks: list[DayPlanBlockOut]
