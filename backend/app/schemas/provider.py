import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProviderProfileBase(BaseModel):
    provider_type: str = Field(..., max_length=32)
    display_name: str = Field(..., max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    photo_url: str | None = Field(default=None, max_length=255)
    license_number: str | None = Field(default=None, max_length=120)
    years_experience: int | None = Field(default=None, ge=0)
    consultation_fee_paise: int | None = Field(default=None, ge=0)


class ProviderProfileCreate(ProviderProfileBase):
    pass


class ProviderProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    photo_url: str | None = Field(default=None, max_length=255)
    license_number: str | None = Field(default=None, max_length=120)
    years_experience: int | None = Field(default=None, ge=0)
    consultation_fee_paise: int | None = Field(default=None, ge=0)


class DoctorDetailBase(BaseModel):
    registration_number: str | None = Field(default=None, max_length=120)
    qualifications: str | None = Field(default=None, max_length=1000)
    specializations: str | None = Field(default=None, max_length=1000)
    languages: str | None = Field(default=None, max_length=255)
    teleconsult_enabled: bool = Field(default=False)
    home_visit_enabled: bool = Field(default=False)


class DoctorDetailCreate(DoctorDetailBase):
    pass


class DoctorDetailUpdate(BaseModel):
    registration_number: str | None = Field(default=None, max_length=120)
    qualifications: str | None = Field(default=None, max_length=1000)
    specializations: str | None = Field(default=None, max_length=1000)
    languages: str | None = Field(default=None, max_length=255)
    teleconsult_enabled: bool | None = Field(default=None)
    home_visit_enabled: bool | None = Field(default=None)


class LabDetailBase(BaseModel):
    accreditation: str | None = Field(default=None, max_length=255)
    home_collection_enabled: bool = Field(default=False)
    report_turnaround_hours: int | None = Field(default=None, ge=0)
    serviceable_pincodes: str | None = Field(default=None, max_length=2000)


class LabDetailCreate(LabDetailBase):
    pass


class LabDetailUpdate(BaseModel):
    accreditation: str | None = Field(default=None, max_length=255)
    home_collection_enabled: bool | None = Field(default=None)
    report_turnaround_hours: int | None = Field(default=None, ge=0)
    serviceable_pincodes: str | None = Field(default=None, max_length=2000)


class ProviderClaimBase(BaseModel):
    profile_id: uuid.UUID


class ProviderClaimCreate(ProviderClaimBase):
    pass


class ProviderClaimOut(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    claimed_by_user_id: uuid.UUID
    status: str
    reviewed_by_user_id: uuid.UUID | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DoctorAvailabilityBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: str = Field(..., max_length=8)
    end_time: str = Field(..., max_length=8)
    slot_duration_minutes: int = Field(default=30, ge=5, le=120)
    is_active: bool = Field(default=True)


class DoctorAvailabilityCreate(DoctorAvailabilityBase):
    pass


class DoctorAvailabilityUpdate(BaseModel):
    start_time: str | None = Field(default=None, max_length=8)
    end_time: str | None = Field(default=None, max_length=8)
    slot_duration_minutes: int | None = Field(default=None, ge=5, le=120)
    is_active: bool | None = Field(default=None)


class DoctorAvailabilityOut(DoctorAvailabilityBase):
    id: uuid.UUID
    provider_profile_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderProfileOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    provider_type: str
    display_name: str
    slug: str
    bio: str | None
    photo_url: str | None
    license_number: str | None
    years_experience: int | None
    consultation_fee_paise: int | None
    verification_status: str
    verification_notes: str | None
    verified_at: datetime | None
    verified_by_user_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
