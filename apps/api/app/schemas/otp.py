from pydantic import BaseModel


class SendOtpRequest(BaseModel):
    email: str


class VerifyOtpRequest(BaseModel):
    email: str
    code: str


class OtpResponse(BaseModel):
    message: str
