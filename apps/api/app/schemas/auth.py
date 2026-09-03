from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

HANDLE_RE = re.compile(r"^[a-z][a-z0-9_]{2,29}$")
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,128}$")


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    handle: str = Field(min_length=3, max_length=30)
    full_name: str | None = Field(default=None, max_length=120)
    terms_version: str = Field(default="2026-09-01", max_length=32)
    privacy_version: str = Field(default="2026-09-01", max_length=32)
    medical_disclaimer_version: str = Field(default="2026-09-01", max_length=32)

    @field_validator("handle")
    @classmethod
    def validate_handle(cls, v: str) -> str:
        handle = v.lower().strip()
        if not HANDLE_RE.match(handle):
            raise ValueError("Handle must be 3–30 chars, start with a letter, and use a-z, 0-9, _ only.")
        return handle

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_RE.match(v):
            raise ValueError("Password must include upper, lower, and a digit (min 8 characters).")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = Field(default=None, max_length=12)
    device_label: str | None = Field(default=None, max_length=120)


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_RE.match(v):
            raise ValueError("Password must include upper, lower, and a digit (min 8 characters).")
        return v


class UpdatePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not PASSWORD_RE.match(v):
            raise ValueError("Password must include upper, lower, and a digit (min 8 characters).")
        return v


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    handle: str | None
    role: str
    full_name: str | None
    family_id: uuid.UUID | None
    is_verified: bool
    totp_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    user: UserOut
    tokens: AccessTokenResponse | None = None
    message: str | None = None
    tfa_required: bool = False


class MessageResponse(BaseModel):
    message: str


class SessionOut(BaseModel):
    id: uuid.UUID
    device_label: str | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime
    is_current: bool = False

    model_config = {"from_attributes": True}


class TotpEnrollResponse(BaseModel):
    secret: str
    otpauth_url: str


class TotpConfirmRequest(BaseModel):
    code: str = Field(min_length=6, max_length=12)


class TotpConfirmResponse(BaseModel):
    backup_codes: list[str]
    message: str = "Two-factor authentication enabled."
