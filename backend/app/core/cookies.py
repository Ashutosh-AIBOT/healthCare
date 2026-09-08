from fastapi import Response

from app.core.config import settings

REFRESH_COOKIE = "aarogya_refresh"


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    # Must mirror set_refresh_cookie attributes so browsers correctly delete the cookie
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path="/api/v1/auth",
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
    )
    # Also clear the rewritten Path=/ variant set by Next.js BFF proxy
    response.delete_cookie(
        key=REFRESH_COOKIE,
        path="/",
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
    )
