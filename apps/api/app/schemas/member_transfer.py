import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class MemberTransferCreate(BaseModel):
    member_id: uuid.UUID
    to_family_id: uuid.UUID


class MemberTransferOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    from_family_id: uuid.UUID
    to_family_id: uuid.UUID
    status: str
    requested_by_user_id: uuid.UUID
    confirmed_by_user_id: uuid.UUID | None
    from_family_confirmed_by: uuid.UUID | None = None
    to_family_confirmed_by: uuid.UUID | None = None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
