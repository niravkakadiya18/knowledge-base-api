from typing import Optional
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    APP_NAME: str = "Knowledge Base API"
    DEBUG: bool = True
    RATE_LIMIT_DEFAULT: str = "100/minute"

    # Database (used by psycopg2 & scripts)
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "jma_knowledge_base"
    DATABASE_USER: str = "jma_user"
    DATABASE_PASSWORD: str = ""
    
    # Capture DATABASE_URL from environment (e.g. Render)
    DATABASE_URL_ENV: Optional[str] = Field(None, validation_alias="DATABASE_URL")

    # Auth
    SECRET_KEY: str = "change_this_to_a_secure_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def DATABASE_URL(self) -> str:
        import os
        url = os.getenv("DATABASE_URL")
        if url:
             return url
        if self.DATABASE_URL_ENV:
            return self.DATABASE_URL_ENV
        return f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings: Settings = get_settings()
print(f"DEBUG: DATABASE_URL ENV VAR: {settings.DATABASE_URL_ENV}")
print(f"DEBUG: FINAL DATABASE_URL: {settings.DATABASE_URL}")
