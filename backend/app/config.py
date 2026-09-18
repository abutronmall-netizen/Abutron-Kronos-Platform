from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ABUTRON_",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    database_url: str = "postgresql+asyncpg://abutron:change-me@localhost:5432/abutron"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "development-only-change-me-please-32-chars"
    jwt_issuer: str = "abutron-platform"
    access_token_minutes: int = 30

    service_token: str = "development-service-token"
    kronos_engine_url: str = "http://127.0.0.1:8090"
    kronos_engine_token: str = "development-engine-token"
    kronos_push_enabled: bool = False

    auto_create_schema: bool = False
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("ABUTRON_JWT_SECRET must be at least 32 characters")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
