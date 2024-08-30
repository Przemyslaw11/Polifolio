from shared.logging_config import setup_logging
from fastapi_app.models.user import Base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os

logger = setup_logging()
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_URL = f"postgresql://user:{POSTGRES_PASSWORD}@db/polifolio"

logger.info(f"Connecting to database: {DATABASE_URL}")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    logger.info("Initializing database")
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
