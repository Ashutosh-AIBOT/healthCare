from pydantic import BaseModel, EmailStr, Field


class SendOtpRequest(BaseModel):
    email: EmailStr
    purpose: str = Field(default="verify_email", pattern="^(verify_email|password_reset)$")


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)
    purpose: str = Field(default="verify_email", pattern="^(verify_email|password_reset)$")


class OtpResponse(BaseModel):
    message: str
