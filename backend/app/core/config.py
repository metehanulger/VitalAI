import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Acil Servis Ön Triaj ve Yönlendirme Servisi (VitialAI)"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api"
    
    # -------------------------------------------------------------
    # Evrensel LLM Konfigürasyonu (İstediğiniz herhangi bir LLM)
    # -------------------------------------------------------------
    # Sağlayıcı seçenekleri: 'openai_compatible', 'gemini', 'watsonx', 'deepseek', 'groq', 'ollama'
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai_compatible")
    
    # Herhangi bir LLM'in API Anahtarı (Boş bırakılmıştır; buraya dilediğiniz API key'i yazabilirsiniz)
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    
    # LLM API Uç Noktası (Base URL)
    # Örnekler:
    # OpenAI: https://api.openai.com/v1
    # DeepSeek: https://api.deepseek.com
    # Groq: https://api.groq.com/openai/v1
    # Yerel Ollama: http://localhost:11434/v1
    # OpenRouter: https://openrouter.ai/api/v1
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    
    # Model Adı (Örn: gpt-4o-mini, deepseek-chat, llama-3.3-70b-versatile, qwen2.5, mistral vb.)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Google Gemini API Konfigürasyonu (Alternatif)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # IBM WatsonX Konfigürasyonu (Alternatif)
    WATSONX_API_KEY: Optional[str] = os.getenv("WATSONX_API_KEY", "")
    WATSONX_PROJECT_ID: Optional[str] = os.getenv("WATSONX_PROJECT_ID", "")
    WATSONX_URL: str = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    WATSONX_MODEL_ID: str = os.getenv("WATSONX_MODEL_ID", "ibm/granite-13b-chat-v2")
    
    # Veritabanı Konfigürasyonu (IBM DB2 & SQLite Fallback)
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./triaj.db")
    DB2_DATABASE: str = os.getenv("DB2_DATABASE", "TRIAGEDB")
    DB2_HOSTNAME: str = os.getenv("DB2_HOSTNAME", "localhost")
    DB2_PORT: int = int(os.getenv("DB2_PORT", "50000"))
    DB2_PROTOCOL: str = os.getenv("DB2_PROTOCOL", "TCPIP")
    DB2_UID: str = os.getenv("DB2_UID", "db2inst1")
    DB2_PWD: str = os.getenv("DB2_PWD", "password123")
    DB2_SECURITY: Optional[str] = os.getenv("DB2_SECURITY", None)
    
    # Yerel SQLite Geliştirme Yolu
    SQLITE_PATH: str = os.getenv("SQLITE_PATH", "triage_local.sqlite3")

    class Config:
        case_sensitive = False
        env_file = ".env"
        extra = "ignore"

settings = Settings()
