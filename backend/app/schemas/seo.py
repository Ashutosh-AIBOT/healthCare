from datetime import datetime

from pydantic import BaseModel, Field


class SEOPageBase(BaseModel):
    route: str = Field(..., max_length=255)
    title: str = Field(..., max_length=255)
    description: str = Field(..., max_length=2000)
    canonical_url: str | None = Field(default=None, max_length=500)
    robots_noindex: bool = Field(default=False)
    robots_nofollow: bool = Field(default=False)
    quality_gate_passed: bool = Field(default=False)
    last_verified_at: datetime | None = Field(default=None)


class SEOPageCreate(SEOPageBase):
    pass


class SEOPageUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    canonical_url: str | None = Field(default=None, max_length=500)
    robots_noindex: bool | None = Field(default=None)
    robots_nofollow: bool | None = Field(default=None)
    quality_gate_passed: bool | None = Field(default=None)
    last_verified_at: datetime | None = Field(default=None)


class SEOPageOut(SEOPageBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderSEOPageBase(BaseModel):
    provider_profile_id: str
    route: str = Field(..., max_length=255)
    quality_score: float = Field(..., ge=0.0, le=1.0)
    is_indexable: bool = Field(default=True)
    last_crawled_at: datetime | None = Field(default=None)
    crawl_error: str | None = Field(default=None, max_length=2000)


class ProviderSEOPageCreate(ProviderSEOPageBase):
    pass


class ProviderSEOPageUpdate(BaseModel):
    route: str | None = Field(default=None, max_length=255)
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    is_indexable: bool | None = Field(default=None)
    last_crawled_at: datetime | None = Field(default=None)
    crawl_error: str | None = Field(default=None, max_length=2000)


class ProviderSEOPageOut(ProviderSEOPageBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SEOCheckRequest(BaseModel):
    routes: list[str] = Field(default_factory=list, max_length=50)


class SEOCheckItem(BaseModel):
    route: str
    exists: bool
    title_length: int | None = None
    description_length: int | None = None
    has_canonical: bool | None = None
    robots_noindex: bool | None = None
    robots_nofollow: bool | None = None
    quality_gate_passed: bool | None = None
    issues: list[str] = Field(default_factory=list)


class SEOCheckResponse(BaseModel):
    checks: list[SEOCheckItem]
    overall_ok: bool
