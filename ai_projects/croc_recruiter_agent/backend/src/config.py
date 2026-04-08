from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    # Core
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Database
    DATABASE_PATH: str = "data/staffing.db"

    # Direct Postgres (Supabase or any Postgres)
    DATABASE_URL: str = ""

    # Web
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # MCP
    MCP_TOOLS_JSON: str = "[]"

    # Office Postgres
    OFFICE_DB_DSN: str = ""

    # Supabase (PostgREST API)
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # System defaults
    DEFAULT_USER_ID: str = "carol.chen"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Helpers
    @property
    def is_dev(self) -> bool:
        return self.ENV.lower() == "development"

    @property
    def db_path(self) -> Path:
        return Path(self.DATABASE_PATH)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
