from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

DATABASE_URL = (settings.database_url or "").replace("postgresql://", "postgresql+asyncpg://")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True) if DATABASE_URL else None
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False) if engine else None

class Base(DeclarativeBase):
    pass

async def get_db():
    if async_session_maker is None:
        raise RuntimeError("DATABASE_URL is not configured.")
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    if engine is None:
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
