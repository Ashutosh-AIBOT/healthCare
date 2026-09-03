import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class FamilyMemberCreate(BaseModel):
    user_id: uuid.UUID | None = Field(default=None)
    relation: str | None = Field(default=None, max_length=32)
    date_of_birth: date | None = Field(default=None)
    gender: str | None = Field(default=None, max_length=32)
    blood_group: str | None = Field(default=None, max_length=32)
    is_dependent: bool = Field(default=False)
    guardian_id: uuid.UUID | None = Field(default=None)
    timezone: str = Field(default="Asia/Kolkata", max_length=64)
    diet_preference: str | None = Field(default=None, max_length=32)


class FamilyMemberUpdate(BaseModel):
    relation: str | None = Field(default=None, max_length=32)
    date_of_birth: date | None = Field(default=None)
    gender: str | None = Field(default=None, max_length=32)
    blood_group: str | None = Field(default=None, max_length=32)
    is_dependent: bool | None = Field(default=None)
    guardian_id: uuid.UUID | None = Field(default=None)
    timezone: str | None = Field(default=None, max_length=64)
    diet_preference: str | None = Field(default=None, max_length=32)


class FamilyMemberOut(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    user_id: uuid.UUID | None
    relation: str | None
    date_of_birth: date | None
    gender: str | None
    blood_group: str | None
    is_dependent: bool
    guardian_id: uuid.UUID | None
    timezone: str
    diet_preference: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
