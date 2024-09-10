import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from shared.logging_config import setup_logging
from fastapi_app.models.user import Base

logger = setup_logging()
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_URL = f"postgresql+asyncpg://user:{POSTGRES_PASSWORD}@db/polifolio"

logger.info(f"Connecting to database: {DATABASE_URL}")
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """
    Initialize the database by creating all tables.
    """
    logger.info("Initializing database")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def get_db() -> AsyncSession:
    """
    Dependency to get the database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
