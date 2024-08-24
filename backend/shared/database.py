from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from .models import Base
import logging
import os

logging.basicConfig(level=logging.INFO)

POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DATABASE_URL = f"postgresql://user:{POSTGRES_PASSWORD}@db/polifolio"

logging.info(f"Connecting to database: {DATABASE_URL}")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    logging.info("Initializing database")
    Base.metadata.create_all(bind=engine)
    logging.info("Database initialized")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
