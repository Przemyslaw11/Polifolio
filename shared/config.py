from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import model_validator
import logging

from shared.logging_config import setup_logging, get_logger


class Settings(BaseSettings):
    # .env
    FASTAPI_SECRET_KEY: str
    FASTAPI_URL: str
    ALPHAVANTAGE_API_KEY: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_USER: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    BACKGROUND_IMAGE_PATH: str
    STOCK_PRICES_INTERVAL_UPDATES_SECONDS: int
    PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS: int

    # Authorization
    pwd_context: ClassVar[CryptContext] = CryptContext(
        schemes=["bcrypt"], deprecated="auto"
    )
    oauth2_scheme: ClassVar[OAuth2PasswordBearer] = OAuth2PasswordBearer(
        tokenUrl="token"
    )

    # Derived
    DATABASE_URL: str = ""
    MISFIRE_GRACE_TIME_SECONDS: int = 0

    # Helpful
    LOG_FILE: str
    TIMEZONE: str

    # Logging
    logger: ClassVar[logging.Logger]

    @model_validator(mode="after")
    def compute_derived_settings(cls, values):
        values.DATABASE_URL = f"postgresql+asyncpg://{values.POSTGRES_USER}:{values.POSTGRES_PASSWORD}@db/{values.POSTGRES_DB}"
        values.MISFIRE_GRACE_TIME_SECONDS = (
            values.STOCK_PRICES_INTERVAL_UPDATES_SECONDS
            + values.PORTFOLIO_HISTORY_UPDATE_INTERVAL_SECONDS
        ) // 2
        return values

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", arbitrary_types_allowed=True
    )


settings = Settings()
setup_logging(settings.LOG_FILE, settings.TIMEZONE)
logger = get_logger("global")
