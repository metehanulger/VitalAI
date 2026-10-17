import os
from datetime import datetime
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILES = (
    str(PROJECT_ROOT / ".env"),
    str(PROJECT_ROOT / "backend" / ".env"),
)


def yerel_simdi() -> datetime:
    """Return the current Istanbul time as a naive datetime for database storage."""
    return datetime.now(ZoneInfo("Europe/Istanbul")).replace(tzinfo=None)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Emergency Department Pre-Triage and Routing Service (VitialAI)"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api"
    DB_AUTO_CREATE: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    TRIAGE_URGENCY_MODEL: Optional[str] = None
    TRIAGE_SPECIALTY_MODEL: Optional[str] = None

    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai_compatible")

    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")

    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    WATSONX_API_KEY: Optional[str] = os.getenv("WATSONX_API_KEY", "")
    WATSONX_PROJECT_ID: Optional[str] = os.getenv("WATSONX_PROJECT_ID", "")
    WATSONX_URL: str = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    WATSONX_MODEL_ID: str = os.getenv("WATSONX_MODEL_ID", "ibm/granite-13b-chat-v2")

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./triaj.db")
    DB2_DATABASE: str = os.getenv("DB2_DATABASE", "TRIAGEDB")
    DB2_HOSTNAME: str = os.getenv("DB2_HOSTNAME", "localhost")
    DB2_PORT: int = int(os.getenv("DB2_PORT", "50000"))
    DB2_PROTOCOL: str = os.getenv("DB2_PROTOCOL", "TCPIP")
    DB2_UID: str = os.getenv("DB2_UID", "db2inst1")
    DB2_PWD: str = os.getenv("DB2_PWD", "password123")
    DB2_SECURITY: Optional[str] = os.getenv("DB2_SECURITY", None)

    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "triage_local.sqlite3")

    @property
    def app_name(self) -> str:
        return self.PROJECT_NAME

    @property
    def db_auto_create(self) -> bool:
        return self.DB_AUTO_CREATE

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def watsonx_enabled(self) -> bool:
        return bool(self.WATSONX_API_KEY and self.WATSONX_PROJECT_ID)

    class Config:
        case_sensitive = False
        env_file = ENV_FILES
        extra = "ignore"

settings = Settings()
