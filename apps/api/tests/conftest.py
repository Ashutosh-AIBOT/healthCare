import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_db
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    eng = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True, poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest.fixture(scope="session")
async def app_user_engine():
    eng = create_async_engine(
        "postgresql+asyncpg://app_user:app_pass@postgres:5432/aarogya",
        echo=False,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
    yield eng
    await eng.dispose()


@pytest.fixture(scope="session", autouse=True)
async def clean_db(engine):
    async with engine.connect() as conn:
        await conn.execute(text("TRUNCATE TABLE sessions, otp_codes, users, families RESTART IDENTITY CASCADE"))
        await conn.commit()


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
