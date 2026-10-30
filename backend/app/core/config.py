"""Application settings.

This is the single source of configuration. Values are read, in order of
priority, from environment variables, then the repository-root ``.env``, then
``backend/.env``, then the defaults below. Names are case-insensitive.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILES = (
    str(PROJECT_ROOT / ".env"),
    str(PROJECT_ROOT / "backend" / ".env"),
)


def yerel_simdi() -> datetime:
    """Return the current Istanbul time as a naive datetime for database storage."""
    return datetime.now(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=ENV_FILES, extra="ignore")

    PROJECT_NAME: str = "Emergency Department Pre-Triage and Routing Service (VitialAI)"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

    # Database (PostgreSQL only)
    DATABASE_URL: str = "postgresql+psycopg://triaj:triaj_sifre@localhost:5432/triajdb"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    # Run Alembic migrations (alembic upgrade head) when the API starts
    DB_AUTO_MIGRATE: bool = True

    # Departments the triage may recommend (comma-separated English names).
    # Empty uses the default list in app/core/poliklinikler.py.
    POLIKLINIKLER: str = ""

    # Local ML artifacts
    TRIAGE_URGENCY_MODEL: Optional[str] = None
    TRIAGE_SPECIALTY_MODEL: Optional[str] = None

    # LLM provider: openai_compatible, gemini, or watsonx
    LLM_PROVIDER: str = "openai_compatible"
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt-4o-mini"
    # Timeout for the main triage call; Gemini uses GEMINI_TIMEOUT_SECONDS
    LLM_TIMEOUT_SECONDS: float = 30
    # Shorter timeout for the complaint normalization call that feeds both ML models
    LLM_TRANSLATION_TIMEOUT_SECONDS: float = 15

    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    # Tried in order when the primary model fails (quota, unavailable, or timeout).
    # Free-tier quotas are counted per model, so fallbacks also extend the daily limit.
    GEMINI_FALLBACK_MODELS: str = "gemini-3-flash-preview,gemini-3.1-flash-lite"
    GEMINI_TIMEOUT_SECONDS: float = 60

    WATSONX_API_KEY: str = ""
    WATSONX_PROJECT_ID: str = ""
    WATSONX_URL: str = "https://us-south.ml.cloud.ibm.com"
    WATSONX_MODEL_ID: str = "ibm/granite-13b-chat-v2"

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def app_name(self) -> str:
        return self.PROJECT_NAME

    @property
    def db_auto_migrate(self) -> bool:
        return self.DB_AUTO_MIGRATE

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def watsonx_enabled(self) -> bool:
        return bool(self.WATSONX_API_KEY and self.WATSONX_PROJECT_ID)


settings = Settings()
