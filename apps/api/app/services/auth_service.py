import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import UserRole
from app.models.user import Session, User
from app.schemas.auth import AuthResponse, RegisterRequest, TokenResponse, UserOut


def _hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    async def register(self, db: AsyncSession, payload: RegisterRequest) -> AuthResponse:
        existing = await db.scalar(select(User).where(User.email == payload.email.lower()))
        if existing:
            raise AppError(
                code="AUTH_EMAIL_EXISTS",
                status=409,
                detail="An account with this email already exists.",
            )

        user = User(
            email=payload.email.lower(),
            password_hash=hash_password(payload.password),
            full_name=payload.full_name,
            role=UserRole.FAMILY_OWNER,
            is_verified=settings.otp_dev_mode,
        )
        db.add(user)
        await db.flush()

        tokens = await self._issue_tokens(db, user)
        return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)

    async def login(self, db: AsyncSession, email: str, password: str) -> AuthResponse:
        user = await db.scalar(select(User).where(User.email == email.lower()))
        if user is None or not verify_password(password, user.password_hash):
            raise AppError(
                code="AUTH_INVALID_CREDENTIALS",
                status=401,
                detail="That email and password do not match.",
            )

        tokens = await self._issue_tokens(db, user)
        return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)

    async def refresh(self, db: AsyncSession, refresh_token: str) -> TokenResponse:
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
            session.revoked_at = datetime.now(UTC)
            raise AppError(
                code="AUTH_REFRESH_REUSED",
                status=401,
                detail="Refresh token reuse detected. Please sign in again.",
            )

        user = await db.get(User, user_id)
        if user is None:
            raise AppError(
                code="AUTH_TOKEN_INVALID",
                status=401,
                detail="Invalid or expired refresh token.",
            )

        session.revoked_at = datetime.now(UTC)
        return await self._issue_tokens(db, user)

    async def get_user(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        user = await db.get(User, user_id)
        if user is None:
            raise AppError(code="NOT_FOUND", status=404, detail="User not found.")
        return user

    async def _issue_tokens(self, db: AsyncSession, user: User) -> TokenResponse:
        session_row = Session(
            user_id=user.id,
            refresh_token_hash="",
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
        )
        db.add(session_row)
        await db.flush()

        refresh_token = create_refresh_token(user.id, session_row.id)
        session_row.refresh_token_hash = _hash_refresh_token(refresh_token)
        session_row.last_used_at = datetime.now(UTC)

        access_token = create_access_token(user.id, user.role)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )


auth_service = AuthService()
