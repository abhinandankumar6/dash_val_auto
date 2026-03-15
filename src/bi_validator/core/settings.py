from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "BI Dashboard Validator"
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    database_url: str = Field(
        default="postgresql+psycopg://validator:validator@postgres:5432/bi_validator",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    queue_name: str = Field(default="dashboard-validation", alias="QUEUE_NAME")
    queue_backend: str = Field(default="redis", alias="QUEUE_BACKEND")
    auto_create_tables: bool = Field(default=True, alias="AUTO_CREATE_TABLES")

    report_root: Path = Field(default=Path("output/reports"), alias="REPORT_ROOT")
    screenshot_root: Path = Field(default=Path("output/screenshots"), alias="SCREENSHOT_ROOT")

    playwright_headless: bool = Field(default=True, alias="PLAYWRIGHT_HEADLESS")
    playwright_slow_mo_ms: int = Field(default=0, alias="PLAYWRIGHT_SLOW_MO_MS")
    playwright_timeout_ms: int = Field(default=15000, alias="PLAYWRIGHT_TIMEOUT_MS")
    navigation_max_depth: int = Field(default=4, alias="NAVIGATION_MAX_DEPTH")

    llm_provider: str = Field(default="disabled", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-4.1-mini", alias="LLM_MODEL")
    llm_base_url: str | None = Field(default=None, alias="LLM_BASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
