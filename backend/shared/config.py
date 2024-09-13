from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator


class Settings(BaseSettings):
    # .env
    FASTAPI_SECRET_KEY: str
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

    # Derived
    DATABASE_URL: str = ""
    MISFIRE_GRACE_TIME_SECONDS: int = 0

    # Helpful
    LOG_FILE: str = "app.log"
    TIMEZONE: str = "Europe/Warsaw"

    @model_validator(mode="after")
    def compute_derived_settings(cls, values):
        values.DATABASE_URL = f"postgresql+asyncpg://{values.POSTGRES_USER}:{values.POSTGRES_PASSWORD}@db/{values.POSTGRES_DB}"
        values.MISFIRE_GRACE_TIME_SECONDS = (
            values.STOCK_PRICES_INTERVAL_UPDATES_SECONDS
            + values.STOCK_PRICES_INTERVAL_UPDATES_SECONDS
        ) // 2

        return values

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
