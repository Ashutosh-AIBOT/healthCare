import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.sql import expression as sql_exp

from app.core.config import settings
from app.core.errors import AppError
from app.integrations.email import send_otp_email
from app.models.otp import OtpCode
from app.schemas.otp import SendOtpRequest, VerifyOtpRequest


class OtpService:
    @staticmethod
    def _hash(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    async def send(self, db, payload: SendOtpRequest) -> None:
        code = settings.otp_dev_code if settings.otp_dev_mode else f"{uuid.uuid4().int % 1000000:06d}"
        expires_at = datetime.now(UTC) + timedelta(minutes=10)
        row = OtpCode(
            email=payload.email.lower(),
            code_hash=self._hash(code),
            purpose="verify_email",
            expires_at=expires_at,
        )
        db.add(row)
        await db.flush()
        if not settings.otp_dev_mode:
            send_otp_email(payload.email, code)
        else:
            return code

    async def verify(self, db, payload: VerifyOtpRequest) -> None:
        row = await db.scalar(
            select(OtpCode).where(
                OtpCode.email == payload.email.lower(),
                OtpCode.purpose == "verify_email",
                OtpCode.consumed_at.is_(None),
            )
        )
        if row is None or row.expires_at < datetime.now(UTC):
            raise AppError(code="OTP_INVALID", status=400, detail="Invalid or expired OTP.")
        if row.code_hash != self._hash(payload.code):
            raise AppError(code="OTP_INVALID", status=400, detail="Invalid OTP.")
        row.consumed_at = datetime.now(UTC)


otp_service = OtpService()
