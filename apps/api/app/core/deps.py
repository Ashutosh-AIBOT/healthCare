import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import auth_service

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            code="AUTH_TOKEN_INVALID",
            status=401,
            detail="Authentication required.",
        )
    try:
        payload = decode_token(credentials.credentials, "access")
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise AppError(
            code="AUTH_TOKEN_INVALID",
            status=401,
            detail="Invalid or expired access token.",
        ) from exc

    return await auth_service.get_user(db, user_id)
