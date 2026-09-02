import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MemberMedicalProfileCreate(BaseModel):
    conditions: str | None = Field(default=None, max_length=2000)
    allergies: str | None = Field(default=None, max_length=2000)
    medications: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    is_complete: bool = Field(default=False)


class MemberMedicalProfileUpdate(BaseModel):
    conditions: str | None = Field(default=None, max_length=2000)
    allergies: str | None = Field(default=None, max_length=2000)
    medications: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    is_complete: bool | None = Field(default=None)


class MemberMedicalProfileOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    conditions: str | None
    allergies: str | None
    medications: str | None
    notes: str | None
    is_complete: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
