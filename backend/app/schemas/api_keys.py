"""Schema for LLM provider API keys."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, validator


ProviderName = Literal["nvidia", "openai", "gemini", "groq", "ollama", "mock", "telegram"]


class ApiKeyCreate(BaseModel):
    """Create a new API key entry."""

    provider: ProviderName = Field(..., description="LLM provider name")
    api_key: str = Field(..., min_length=10, description="Raw API key (will be hashed)")

    @validator("provider")
    def provider_must_be_valid(cls, v: str) -> str:
        valid = ["nvidia", "openai", "gemini", "groq", "ollama", "mock", "telegram"]
        if v not in valid:
            raise ValueError(f"Provider must be one of: {valid}")
        return v


class ApiKeyUpdate(BaseModel):
    """Update an existing API key (e.g., deactivate)."""

    is_active: Optional[bool] = Field(None, description="Whether the key is active")


class ApiKeyRead(BaseModel):
    """Read API key info (hash only, never the raw key)."""

    id: uuid.UUID
    provider: ProviderName
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
