from sqlalchemy.orm import Session, sessionmaker
from shared.logging_config import setup_logging
from fastapi_app.models.user import Base
from sqlalchemy import create_engine
import os

logger = setup_logging()
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_URL = f"postgresql://user:{POSTGRES_PASSWORD}@db/polifolio"

logger.info(f"Connecting to database: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    args: None
    return: None
    """
    logger.info("Initializing database")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def get_db() -> Session:
    """
    Dependency to get the database session.
    args: None
    return: A database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
