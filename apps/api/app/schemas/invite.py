import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class InviteCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="family_member", max_length=32)
    relation: str | None = Field(default=None, max_length=32)
    expires_in_hours: int = Field(default=72, gt=0, le=168)


class InviteOut(BaseModel):
    id: uuid.UUID
    family_id: uuid.UUID
    email: str
    role: str
    relation: str | None
    status: str
    expires_at: datetime
    accepted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
