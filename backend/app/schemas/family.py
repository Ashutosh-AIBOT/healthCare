import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class FamilyCreate(BaseModel):
    name: str = Field(max_length=120)


class FamilyOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
