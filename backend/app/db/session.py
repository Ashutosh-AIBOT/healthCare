import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.db.base import Base

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, None)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def set_tenant_context(session: AsyncSession, family_id: uuid.UUID | None) -> None:
    """SET LOCAL for PgBouncer transaction pooling — never session-level set_config."""
    if family_id is None:
        await session.execute(text("SELECT set_config('app.family_id', '', true)"))
    else:
        fid = str(uuid.UUID(str(family_id)))
        await session.execute(text("SELECT set_config('app.family_id', :fid, true)"), {"fid": fid})


async def set_rls_bypass(session: AsyncSession, enabled: bool) -> None:
    """Auth bootstrap lookups need a temporary RLS bypass — never leave this on."""
    value = "on" if enabled else "off"
    await session.execute(text("SELECT set_config('app.bypass_rls', :v, true)"), {"v": value})


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class UserRole:
    FAMILY_OWNER = "family_owner"
    FAMILY_ADMIN = "family_admin"
    FAMILY_MEMBER = "family_member"
    DOCTOR = "doctor"
    LAB_ADMIN = "lab_admin"
    LAB_STAFF = "lab_staff"
    PLATFORM_ADMIN = "platform_admin"
