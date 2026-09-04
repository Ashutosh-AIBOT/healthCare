from typing import Annotated

from fastapi import APIRouter, Body, Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import REFRESH_COOKIE, clear_refresh_cookie, set_refresh_cookie
from app.core.deps import get_current_user
from app.core.errors import AppError
from app.core.ratelimit import check_rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SessionOut,
    TotpConfirmRequest,
    TotpConfirmResponse,
    TotpEnrollResponse,
    UpdatePasswordRequest,
    UserOut,
    VerifyRegistrationRequest,
)
from app.services.auth_service import auth_service
from app.services.totp_service import totp_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=MessageResponse, status_code=202)
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Stage 1: validate + stash pending registration + send OTP. Creates no account rows."""
    await check_rate_limit("auth:register:ip", limit=20, window_seconds=3600)
    return await auth_service.register(db, payload)


@router.post("/verify-registration", response_model=AuthResponse, status_code=201)
async def verify_registration(
    payload: VerifyRegistrationRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Stage 2: prove the OTP → create the account, verified, and sign the user in."""
    result, refresh = await auth_service.verify_registration(db, payload.email, payload.code)
    set_refresh_cookie(response, refresh)
    return result


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    result, refresh = await auth_service.login(
        db,
        payload.email,
        payload.password,
        totp_code=payload.totp_code,
        device_label=payload.device_label,
    )
    if refresh:
        set_refresh_cookie(response, refresh)
    return result


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: Annotated[RefreshRequest | None, Body()] = None,
    aarogya_refresh: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> AccessTokenResponse:
    token = (payload.refresh_token if payload else None) or aarogya_refresh
    if not token:
        raise AppError(code="AUTH_TOKEN_INVALID", status=401, detail="Refresh token required.")
    tokens, new_refresh = await auth_service.refresh(db, token)
    set_refresh_cookie(response, new_refresh)
    return tokens


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: Annotated[RefreshRequest | None, Body()] = None,
    aarogya_refresh: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> MessageResponse:
    token = (payload.refresh_token if payload else None) or aarogya_refresh
    await auth_service.logout(db, token)
    clear_refresh_cookie(response)
    return MessageResponse(message="Signed out.")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    await auth_service.logout_all(db, current_user)
    clear_refresh_cookie(response)
    return MessageResponse(message="All sessions revoked.")


@router.get("/sessions", response_model=list[SessionOut])
async def sessions(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    aarogya_refresh: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> list[SessionOut]:
    return await auth_service.list_sessions(db, current_user, aarogya_refresh)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    message = await auth_service.forgot_password(db, payload.email)
    return MessageResponse(message=message)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    await auth_service.reset_password(db, payload.email, payload.otp, payload.new_password)
    return MessageResponse(message="Password updated. Sign in with your new password.")


@router.patch("/password", response_model=MessageResponse)
async def update_password(
    payload: UpdatePasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    await auth_service.update_password(db, current_user, payload.current_password, payload.new_password)
    return MessageResponse(message="Password updated.")


@router.get("/me", response_model=UserOut)
async def me(current_user: Annotated[User, Depends(get_current_user)]) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post("/2fa/enroll", response_model=TotpEnrollResponse)
async def enroll_2fa(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TotpEnrollResponse:
    secret, uri = await totp_service.enroll(db, current_user)
    return TotpEnrollResponse(secret=secret, otpauth_url=uri)


@router.post("/2fa/confirm", response_model=TotpConfirmResponse)
async def confirm_2fa(
    payload: TotpConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TotpConfirmResponse:
    codes = await totp_service.confirm(db, current_user, payload.code)
    return TotpConfirmResponse(backup_codes=codes)
