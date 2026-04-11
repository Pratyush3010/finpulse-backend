from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,      # detects dead/idle connections and reconnects
    pool_recycle=300,        # recycle connections every 5 min (before Neon suspends)
    pool_size=5,
    max_overflow=0,          # important for serverless/Neon
    connect_args={"ssl": "require"},
)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        from app.models import user, category, transaction, budget, recurring_transaction, savings_goal, group  # noqa
        await conn.run_sync(Base.metadata.create_all)
