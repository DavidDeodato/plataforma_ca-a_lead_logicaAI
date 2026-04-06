from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Lead Outreach MVP"
    app_env: str = Field(default="development", validation_alias=AliasChoices("APP_ENV", "app_env"))
    app_url: str = Field(default="http://localhost:8000", validation_alias=AliasChoices("APP_URL", "app_url"))

    firecrawl_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("FIRECRAWL_API_KEY", "firecrawl_api", "firecrawl_api_key"),
    )
    openai_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    database_url: str = Field(
        default="sqlite:///./local.db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    wasender_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("WASENDER_API_KEY", "wasender_api_key"),
    )
    wasender_webhook_secret: str = Field(
        default="",
        validation_alias=AliasChoices("WASENDER_WEBHOOK_SECRET", "wasender_webhook_secret"),
    )
    wasender_api_base_url: str = Field(
        default="https://www.wasenderapi.com",
        validation_alias=AliasChoices("WASENDER_API_BASE_URL", "wasender_api_base_url"),
    )

    default_niche: str = Field(default="barbearia", validation_alias=AliasChoices("DEFAULT_NICHE", "default_niche"))
    default_city: str = Field(default="Vitoria, ES", validation_alias=AliasChoices("DEFAULT_CITY", "default_city"))
    openai_model: str = Field(default="gpt-4.1-mini", validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"))
    firecrawl_agent_model: str = Field(
        default="spark-1-mini",
        validation_alias=AliasChoices("FIRECRAWL_AGENT_MODEL", "firecrawl_agent_model"),
    )
    firecrawl_agent_max_credits: int = Field(
        default=1500,
        validation_alias=AliasChoices("FIRECRAWL_AGENT_MAX_CREDITS", "firecrawl_agent_max_credits"),
    )
    outreach_daily_limit: int = Field(
        default=20,
        validation_alias=AliasChoices("OUTREACH_DAILY_LIMIT", "outreach_daily_limit"),
    )
    outreach_delay_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices("OUTREACH_DELAY_SECONDS", "outreach_delay_seconds"),
    )
    outbound_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices("OUTBOUND_ENABLED", "outbound_enabled"),
    )
    auto_reply_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("AUTO_REPLY_ENABLED", "auto_reply_enabled"),
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not value:
            return value
        text = str(value).strip()
        if text.startswith("DATABASE_URL="):
            text = text.split("=", 1)[1]
        if text.startswith("postgresql://") and not text.startswith("postgresql+"):
            return text.replace("postgresql://", "postgresql+psycopg://", 1)
        return text

    @property
    def has_wasender_credentials(self) -> bool:
        return bool(self.wasender_api_key)

    @property
    def has_openai_credentials(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_firecrawl_credentials(self) -> bool:
        return bool(self.firecrawl_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
