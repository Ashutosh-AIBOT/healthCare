from urllib.parse import urlparse

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.ratelimit import close_redis
from app.db.session import get_db
from app.main import app


def _app_user_database_url() -> str:
    """Same host/db as DATABASE_URL, but the non-superuser used for RLS checks."""
    raw = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parsed = urlparse(raw)
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    db = (parsed.path or "/aarogya").lstrip("/") or "aarogya"
    return f"postgresql+asyncpg://app_user:app_pass@{host}:{port}/{db}"


@pytest.fixture(scope="session")
async def engine():
    eng = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest.fixture(scope="session", autouse=True)
async def clean_db(engine):
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                DO $$
                BEGIN
                  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
                    CREATE ROLE app_user LOGIN PASSWORD 'app_pass' NOSUPERUSER NOBYPASSRLS;
                  END IF;
                END $$;
                """
            )
        )
        await conn.execute(text("GRANT USAGE ON SCHEMA public TO app_user"))
        await conn.execute(text("GRANT CONNECT ON DATABASE aarogya TO app_user"))
        await conn.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user"))
        await conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user"))
        await conn.execute(
            text(
                "TRUNCATE TABLE backup_codes, totp_secrets, consents, consent_documents, "
                "sessions, otp_codes, consent_access_logs, member_claims, member_visibility_grants, "
                "document_chunks, lab_report_values, documents, jobs, "
                "appointment_events, appointments, "
                "member_transfers, member_medical_profiles, invites, "
                "family_members, users, families RESTART IDENTITY CASCADE"
            )
        )
        await conn.execute(
            text(
                "DO $$ BEGIN "
                "TRUNCATE TABLE document_chunks, lab_report_values, documents, jobs "
                "RESTART IDENTITY CASCADE; "
                "EXCEPTION WHEN undefined_table THEN NULL; END $$"
            )
        )
    yield
    await close_redis()


@pytest.fixture(scope="session")
async def app_user_engine(clean_db):
    eng = create_async_engine(
        _app_user_database_url(),
        echo=False,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    yield eng
    await eng.dispose()


@pytest.fixture
async def db(engine):
    async with engine.connect() as conn:
        async with conn.begin() as transaction:
            session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)(bind=conn)
            yield session
            await transaction.rollback()
            await session.close()


@pytest.fixture
async def db_app_user(app_user_engine):
    async with app_user_engine.connect() as conn:
        async with conn.begin() as transaction:
            session = async_sessionmaker(app_user_engine, class_=AsyncSession, expire_on_commit=False)(bind=conn)
            yield session
            await transaction.rollback()
            await session.close()


@pytest.fixture
async def client(db):
    app.dependency_overrides[get_db] = lambda: db
    transport = ASGITransport(app=app)
    async with AsyncClient(base_url="http://localhost:8000", transport=transport) as ac:
        yield ac
    app.dependency_overrides.clear()
