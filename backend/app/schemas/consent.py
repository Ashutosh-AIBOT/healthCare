import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ConsentAccept(BaseModel):
    consent_type: str = Field(..., max_length=64)
    version: str = Field(..., max_length=32)


class ConsentOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    consent_type: str
    version: str
    accepted_at: datetime
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class ConsentDocumentOut(BaseModel):
    id: uuid.UUID
    consent_type: str
    version: str
    title: str
    body_url: str | None = None

    model_config = {"from_attributes": True}


class ConsentRevoke(BaseModel):
    consent_type: str = Field(..., max_length=64)
