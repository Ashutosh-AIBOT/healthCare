import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.ratelimit import check_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import UserRole, set_rls_bypass, set_tenant_context
from app.models.family import Family
from app.models.user import Consent, Session, User
from app.schemas.auth import (
    AccessTokenResponse,
    AuthResponse,
    RegisterRequest,
    SessionOut,
    UserOut,
)
from app.services.otp_service import otp_service

PROVIDER_ROLES = {
    UserRole.DOCTOR,
    UserRole.LAB_ADMIN,
    UserRole.LAB_STAFF,
    UserRole.PLATFORM_ADMIN,
}


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    async def register(self, db: AsyncSession, payload: RegisterRequest) -> AuthResponse:
        await check_rate_limit(f"auth:register:{payload.email.lower()}", limit=5, window_seconds=3600)
        family: Family | None = None
        user: User | None = None
        await set_rls_bypass(db, True)
        try:
            existing_email = await db.scalar(select(User).where(User.email == payload.email.lower()))
            if existing_email:
                raise AppError(
                    code="AUTH_EMAIL_EXISTS",
                    status=409,
                    detail="An account with this email already exists.",
                )
            existing_handle = await db.scalar(select(User).where(User.handle == payload.handle))
            if existing_handle:
                raise AppError(
                    code="CONFLICT_DUPLICATE",
                    status=409,
                    detail="That handle is already taken.",
                )

            family = Family(name=f"{payload.full_name or payload.handle}'s Family")
            db.add(family)
            await db.flush()

            user = User(
                email=payload.email.lower(),
                handle=payload.handle,
                password_hash=hash_password(payload.password),
                full_name=payload.full_name,
                role=UserRole.FAMILY_OWNER,
                family_id=family.id,
                is_verified=False,
            )
            db.add(user)
            await db.flush()

            now = datetime.now(UTC)
            for consent_type, version in (
                ("terms", payload.terms_version),
                ("privacy", payload.privacy_version),
                ("medical_disclaimer", payload.medical_disclaimer_version),
            ):
                db.add(
                    Consent(
                        user_id=user.id,
                        consent_type=consent_type,
                        version=version,
                        accepted_at=now,
                    )
                )

            await otp_service.send_for_purpose(db, user.email, "verify_email")
        finally:
            await set_rls_bypass(db, False)
            if family is not None:
                await set_tenant_context(db, family.id)

        assert user is not None
        return AuthResponse(
            user=UserOut.model_validate(user),
            tokens=None,
            message="Account created. Verify your email with the OTP we sent.",
        )

    async def login(
        self,
        db: AsyncSession,
        email: str,
        password: str,
        *,
        totp_code: str | None = None,
        device_label: str | None = None,
    ) -> tuple[AuthResponse, str | None]:
        await check_rate_limit(f"auth:login:{email.lower()}", limit=settings.auth_login_rate_limit, window_seconds=60)
        await set_rls_bypass(db, True)
        try:
            user = await db.scalar(select(User).where(User.email == email.lower()))
            if user is None:
                raise AppError(
                    code="AUTH_INVALID_CREDENTIALS",
                    status=401,
                    detail="That email and password do not match.",
                )

            if user.locked_until and user.locked_until > datetime.now(UTC):
                raise AppError(
                    code="AUTH_ACCOUNT_LOCKED",
                    status=423,
                    detail="Account temporarily locked after too many failed attempts.",
                )

            if not verify_password(password, user.password_hash):
                await self._record_failed_login(db, user)
                raise AppError(
                    code="AUTH_INVALID_CREDENTIALS",
                    status=401,
                    detail="That email and password do not match.",
                )

            if not user.is_verified:
                raise AppError(
                    code="AUTH_EMAIL_UNVERIFIED",
                    status=403,
                    detail="Verify your email before signing in.",
                )

            if user.role in PROVIDER_ROLES:
                if not user.totp_enabled:
                    raise AppError(
                        code="TFA_REQUIRED",
                        status=403,
                        detail="Enable two-factor authentication before signing in as a provider.",
                    )
                from app.services.totp_service import totp_service

                if not totp_code or not await totp_service.verify_login_code(db, user, totp_code):
                    raise AppError(code="TFA_INVALID", status=400, detail="Invalid authenticator or backup code.")

            user.failed_login_count = 0
            user.locked_until = None
            refresh, tokens = await self._issue_tokens(db, user, device_label=device_label)
            return (
                AuthResponse(user=UserOut.model_validate(user), tokens=tokens),
                refresh,
            )
        finally:
            await set_rls_bypass(db, False)

    async def refresh(self, db: AsyncSession, refresh_token: str) -> tuple[AccessTokenResponse, str]:
        await set_rls_bypass(db, True)
        try:
            try:
                payload = decode_token(refresh_token, "refresh")
                user_id = uuid.UUID(payload["sub"])
                session_id = uuid.UUID(payload["sid"])
            except (ValueError, KeyError) as exc:
                raise AppError(
                    code="AUTH_TOKEN_INVALID",
                    status=401,
                    detail="Invalid or expired refresh token.",
                ) from exc

            session = await db.get(Session, session_id)
            if session is None or session.user_id != user_id or not session.is_active:
                raise AppError(
                    code="AUTH_TOKEN_INVALID",
                    status=401,
                    detail="Invalid or expired refresh token.",
                )

            if session.refresh_token_hash != _hash_refresh_token(refresh_token):
                await self._revoke_all_sessions(db, user_id)
                raise AppError(
                    code="AUTH_REFRESH_REUSED",
                    status=401,
                    detail="Refresh token reuse detected. All sessions revoked.",
                )

            user = await db.get(User, user_id)
            if user is None:
                raise AppError(
                    code="AUTH_TOKEN_INVALID",
                    status=401,
                    detail="Invalid or expired refresh token.",
                )

            session.revoked_at = datetime.now(UTC)
            new_refresh, tokens = await self._issue_tokens(db, user, device_label=session.device_label)
            return tokens, new_refresh
        finally:
            await set_rls_bypass(db, False)

    async def logout(self, db: AsyncSession, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        await set_rls_bypass(db, True)
        try:
            try:
                payload = decode_token(refresh_token, "refresh")
                session_id = uuid.UUID(payload["sid"])
            except (ValueError, KeyError):
                return
            session = await db.get(Session, session_id)
            if session and session.is_active:
                session.revoked_at = datetime.now(UTC)
        finally:
            await set_rls_bypass(db, False)

    async def logout_all(self, db: AsyncSession, user: User) -> None:
        await set_rls_bypass(db, True)
        try:
            await self._revoke_all_sessions(db, user.id)
        finally:
            await set_rls_bypass(db, False)
            await set_tenant_context(db, user.family_id)

    async def list_sessions(self, db: AsyncSession, user: User, current_refresh: str | None) -> list[SessionOut]:
        await set_tenant_context(db, user.family_id)
        rows = (
            await db.scalars(
                select(Session).where(Session.user_id == user.id, Session.revoked_at.is_(None))
            )
        ).all()
        current_sid = None
        if current_refresh:
            try:
                current_sid = uuid.UUID(decode_token(current_refresh, "refresh")["sid"])
            except (ValueError, KeyError):
                current_sid = None
        return [
            SessionOut(
                id=s.id,
                device_label=s.device_label,
                created_at=s.created_at,
                last_used_at=s.last_used_at,
                expires_at=s.expires_at,
                is_current=s.id == current_sid,
            )
            for s in rows
            if s.is_active
        ]

    async def forgot_password(self, db: AsyncSession, email: str) -> str:
        """Always returns the same message; pads timing. Never reveals whether email exists."""
        from app.core.ratelimit import sleep_pad

        await check_rate_limit(f"auth:forgot:{email.lower()}", limit=3, window_seconds=3600)
        await set_rls_bypass(db, True)
        try:
            user = await db.scalar(select(User).where(User.email == email.lower()))
            if user is not None:
                await otp_service.send_for_purpose(db, email.lower(), "password_reset")
        finally:
            await set_rls_bypass(db, False)
        await sleep_pad(220)
        return "If this email exists, an OTP was sent."

    async def reset_password(self, db: AsyncSession, email: str, otp: str, new_password: str) -> None:
        await set_rls_bypass(db, True)
        try:
            await otp_service.verify_for_purpose(db, email.lower(), otp, "password_reset")
            user = await db.scalar(select(User).where(User.email == email.lower()))
            if user is None:
                raise AppError(code="OTP_INVALID", status=400, detail="Invalid or expired OTP.")
            if verify_password(new_password, user.password_hash):
                raise AppError(
                    code="VALIDATION_FAILED",
                    status=422,
                    detail="New password must differ from the current password.",
                )
            user.password_hash = hash_password(new_password)
            await self._revoke_all_sessions(db, user.id)
        finally:
            await set_rls_bypass(db, False)

    async def update_password(
        self, db: AsyncSession, user: User, current_password: str, new_password: str
    ) -> None:
        if not verify_password(current_password, user.password_hash):
            raise AppError(code="AUTH_INVALID_CREDENTIALS", status=401, detail="Current password is incorrect.")
        if verify_password(new_password, user.password_hash):
            raise AppError(
                code="VALIDATION_FAILED",
                status=422,
                detail="New password must differ from the current password.",
            )
        user.password_hash = hash_password(new_password)
        await self._revoke_all_sessions(db, user.id)

    async def get_user(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        await set_rls_bypass(db, True)
        try:
            user = await db.get(User, user_id)
        finally:
            await set_rls_bypass(db, False)
        if user is None:
            raise AppError(code="NOT_FOUND", status=404, detail="User not found.")
        return user

    async def _record_failed_login(self, db: AsyncSession, user: User) -> None:
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= settings.login_max_failures:
            # Exponential backoff: 15 * 2^(extra-1) minutes, capped
            extra = user.failed_login_count - settings.login_max_failures + 1
            minutes = min(settings.login_lockout_minutes * (2 ** max(extra - 1, 0)), 24 * 60)
            user.locked_until = datetime.now(UTC) + timedelta(minutes=minutes)

    async def _revoke_all_sessions(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        await db.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )

    async def _issue_tokens(
        self, db: AsyncSession, user: User, *, device_label: str | None = None
    ) -> tuple[str, AccessTokenResponse]:
        await set_tenant_context(db, user.family_id)
        session_row = Session(
            user_id=user.id,
            refresh_token_hash="",
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
            device_label=device_label,
        )
        db.add(session_row)
        await db.flush()

        refresh_token = create_refresh_token(user.id, session_row.id)
        session_row.refresh_token_hash = _hash_refresh_token(refresh_token)
        session_row.last_used_at = datetime.now(UTC)

        access_token = create_access_token(user.id, user.role)
        return refresh_token, AccessTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )


auth_service = AuthService()
