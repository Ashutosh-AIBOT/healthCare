import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.errors import AppError
from app.core.ratelimit import check_rate_limit
from app.db.session import set_rls_bypass
from app.integrations.email import send_otp_email
from app.models.otp import OtpCode
from app.models.user import User
from app.schemas.otp import SendOtpRequest, VerifyOtpRequest


class OtpService:
    @staticmethod
    def _hash(code: str) -> str:
        return hashlib.sha256(code.encode()).hexdigest()

    async def send(self, db, payload: SendOtpRequest) -> str | None:
        purpose = payload.purpose or "verify_email"
        return await self.send_for_purpose(db, payload.email.lower(), purpose)

    async def send_for_purpose(self, db, email: str, purpose: str) -> str | None:
        await check_rate_limit(
            f"otp:send:{purpose}:{email}",
            limit=settings.otp_max_sends_per_hour,
            window_seconds=3600,
        )
        code = settings.otp_dev_code if settings.otp_dev_mode else f"{uuid.uuid4().int % 1000000:06d}"
        expires_at = datetime.now(UTC) + timedelta(minutes=10)

        # Invalidate prior unused codes for this purpose
        rows = (
            await db.scalars(
                select(OtpCode).where(
                    OtpCode.email == email,
                    OtpCode.purpose == purpose,
                    OtpCode.consumed_at.is_(None),
                )
            )
        ).all()
        now = datetime.now(UTC)
        for row in rows:
            row.consumed_at = now

        row = OtpCode(
            email=email,
            code_hash=self._hash(code),
            purpose=purpose,
            expires_at=expires_at,
            attempt_count=0,
        )
        db.add(row)
        await db.flush()
        if not settings.otp_dev_mode:
            send_otp_email(email, code)
            return None
        return code

    async def verify(self, db, payload: VerifyOtpRequest) -> None:
        purpose = payload.purpose or "verify_email"
        await self.verify_for_purpose(db, payload.email.lower(), payload.code, purpose)
        if purpose == "verify_email":
            await self._mark_user_verified(db, payload.email.lower())

    async def verify_for_purpose(self, db, email: str, code: str, purpose: str) -> None:
        row = await db.scalar(
            select(OtpCode)
            .where(
                OtpCode.email == email,
                OtpCode.purpose == purpose,
                OtpCode.consumed_at.is_(None),
            )
            .order_by(OtpCode.created_at.desc())
        )
        if row is None:
            raise AppError(code="OTP_INVALID", status=400, detail="Invalid or expired OTP.")
        if row.expires_at < datetime.now(UTC):
            raise AppError(code="OTP_EXPIRED", status=410, detail="OTP has expired.")
        if row.attempt_count >= settings.otp_max_attempts:
            raise AppError(
                code="OTP_ATTEMPTS_EXCEEDED",
                status=429,
                detail="Too many incorrect OTP attempts. Request a new code.",
            )
        if row.code_hash != self._hash(code):
            row.attempt_count += 1
            if row.attempt_count >= settings.otp_max_attempts:
                row.consumed_at = datetime.now(UTC)
                raise AppError(
                    code="OTP_ATTEMPTS_EXCEEDED",
                    status=429,
                    detail="Too many incorrect OTP attempts. Request a new code.",
                )
            raise AppError(code="OTP_INVALID", status=400, detail="Invalid OTP.")
        row.consumed_at = datetime.now(UTC)

    async def _mark_user_verified(self, db, email: str) -> None:
        await set_rls_bypass(db, True)
        try:
            user = await db.scalar(select(User).where(User.email == email))
            if user is None:
                return
            user.is_verified = True
            user.email_verified_at = datetime.now(UTC)
        finally:
            await set_rls_bypass(db, False)


otp_service = OtpService()
