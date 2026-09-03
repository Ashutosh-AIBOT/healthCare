from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.otp import OtpResponse, SendOtpRequest, VerifyOtpRequest
from app.services.otp_service import otp_service

router = APIRouter(prefix="/otp", tags=["otp"])


@router.post("/send", response_model=OtpResponse)
async def send_otp(
    payload: SendOtpRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OtpResponse:
    code = await otp_service.send(db, payload)
    return OtpResponse(message="OTP sent" if code is None else f"Dev OTP: {code}")


@router.post("/verify", response_model=OtpResponse)
async def verify_otp(
    payload: VerifyOtpRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OtpResponse:
    await otp_service.verify(db, payload)
    return OtpResponse(message="OTP verified")
