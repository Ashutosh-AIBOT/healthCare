import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class UserSuspendRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class UserAdminOut(BaseModel):
    id: uuid.UUID
    email: str
    handle: str | None
    full_name: str | None
    role: str
    is_verified: bool
    is_suspended: bool
    suspended_at: datetime | None
    suspended_by_user_id: uuid.UUID | None
    suspended_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserAdminOut]
    total: int
    limit: int
    offset: int
