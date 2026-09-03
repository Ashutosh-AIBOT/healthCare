import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProviderSearchFilters(BaseModel):
    q: str | None = Field(default=None, max_length=200)
    provider_type: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=120)
    specialization: str | None = Field(default=None, max_length=120)
    pincode: str | None = Field(default=None, max_length=10)
    radius_km: int | None = Field(default=None, ge=1, le=5000)
    verified_only: bool = Field(default=False)
    min_fee_paise: int | None = Field(default=None, ge=0)
    max_fee_paise: int | None = Field(default=None, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)


class RankingBreakdown(BaseModel):
    text_match: float = Field(default=0.0)
    verification: float = Field(default=0.0)
    experience: float = Field(default=0.0)
    price: float = Field(default=0.0)
    recency: float = Field(default=0.0)
    composite: float = Field(default=0.0)


class ProviderSearchResult(BaseModel):
    id: uuid.UUID
    provider_type: str
    display_name: str
    slug: str
    city: str | None
    state: str | None
    pincode: str | None
    consultation_fee_paise: int | None
    verification_status: str
    rating: float | None
    response_rate: float | None
    completion_rate: float | None
    years_experience: int | None
    doctor_details: dict[str, Any] | None = None
    lab_details: dict[str, Any] | None = None
    ranking: RankingBreakdown

    model_config = {"from_attributes": True}
