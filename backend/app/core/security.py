from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

ALGORITHM = "HS256"
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _encode(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: UUID, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return _encode(
        {
            "sub": str(user_id),
            "role": role,
            "type": TOKEN_TYPE_ACCESS,
            "jti": str(uuid4()),
            "exp": expire,
        }
    )


def create_refresh_token(user_id: UUID, session_id: UUID) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return _encode(
        {
            "sub": str(user_id),
            "sid": str(session_id),
            "type": TOKEN_TYPE_REFRESH,
            "exp": expire,
        }
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError("invalid token type")
    return payload


# --- JTI revocation via Redis (access_token 15m blacklist) ---

_REDIS_JTI_PREFIX = "revoked_jti:"


async def revoke_jti(jti: str, ttl_seconds: int | None = None) -> None:
    """Mark access token jti as revoked until it naturally expires."""
    ttl = ttl_seconds or settings.access_token_expire_minutes * 60
    try:
        import redis.asyncio as redis  # local import to avoid cycle

        r = redis.from_url(settings.redis_url, decode_responses=True)
        await r.setex(f"{_REDIS_JTI_PREFIX}{jti}", ttl, "1")
        await r.aclose()
    except Exception:
        # Fail-open for revocation write — logout best-effort when Redis down
        pass


async def is_jti_revoked(jti: str) -> bool:
    try:
        import redis.asyncio as redis

        r = redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=0.3, socket_timeout=0.3)
        val = await r.get(f"{_REDIS_JTI_PREFIX}{jti}")
        await r.aclose()
        return val is not None
    except Exception:
        return False
