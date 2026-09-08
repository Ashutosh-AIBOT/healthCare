from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel


class LearnCategoryOut(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    kind: str
    description: str | None
    icon: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class LearnItemOut(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    slug: str
    title: str
    summary: str | None
    content: str | None
    image_url: str | None
    nutrition: dict[str, Any] | None
    benefits: list[str] | None
    healthy_role: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class TestBodyPartOut(BaseModel):
    id: uuid.UUID
    slug: str
    name: str
    order_index: int
    description: str | None

    model_config = {"from_attributes": True}


class BodyTestOut(BaseModel):
    id: uuid.UUID
    body_part_id: uuid.UUID
    name: str
    what_it_checks: str | None
    prep_note: str | None
    fasting_required: bool
    sort_order: int

    model_config = {"from_attributes": True}


class LearnSearchResult(BaseModel):
    query: str
    categories: list[LearnCategoryOut]
    items: list[LearnItemOut]
    tests: list[BodyTestOut]
