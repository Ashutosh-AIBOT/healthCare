import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.visibility import FIELD_KEYS, GrantLevel


class VisibilityGrantItem(BaseModel):
    viewer_member_id: uuid.UUID
    field_key: str = Field(..., max_length=64)
    level: str = Field(default=GrantLevel.VIEW, max_length=32)


class VisibilityGrantOut(BaseModel):
    id: uuid.UUID
    subject_member_id: uuid.UUID
    viewer_member_id: uuid.UUID
    field_key: str
    level: str
    granted_at: datetime
    revoked_at: datetime | None

    model_config = {"from_attributes": True}


class VisibilityGrantsPut(BaseModel):
    grants: list[VisibilityGrantItem] = Field(default_factory=list)


class VisibilityRevokeBody(BaseModel):
    viewer_member_id: uuid.UUID
    field_key: str = Field(..., max_length=64)


class VisibilityLevelsOut(BaseModel):
    subject_member_id: uuid.UUID
    viewer_member_id: uuid.UUID
    grants: dict[str, str]
    field_keys: tuple[str, ...] = FIELD_KEYS


class MemberClaimCreate(BaseModel):
    member_id: uuid.UUID
    claiming_user_id: uuid.UUID | None = None


class MemberClaimConfirm(BaseModel):
    as_guardian: bool = False
    claiming_user_id: uuid.UUID | None = None
    confirm_full_name: str | None = Field(default=None, max_length=120)
    confirm_dob: str | None = Field(default=None, max_length=32)


class MemberClaimOut(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    invited_by_user_id: uuid.UUID
    claiming_user_id: uuid.UUID | None
    status: str
    confirm_full_name: str | None
    confirm_dob: str | None
    guardian_confirmed_at: datetime | None
    member_confirmed_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
