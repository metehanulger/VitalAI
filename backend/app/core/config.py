from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ortam değişkenlerinden (veya backend/.env dosyasından) okunan ayarlar."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Ön Triaj API"

    # Docker'da DB2: db2+ibm_db://db2inst1:sifre@db2:50000/TRIAJDB
    # Yerel geliştirme için varsayılan SQLite dosyasıdır.
    database_url: str = "sqlite:///./triaj.db"
    # DB2'de şemayı database/init.sql kurar; o durumda false yapılır.
    db_auto_create: bool = True

    # Virgülle ayrılmış frontend adresleri (Vite varsayılanı 5173)
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    timezone: str = "Europe/Istanbul"

    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    watsonx_apikey: str = ""
    watsonx_project_id: str = ""
    watsonx_model_id: str = "ibm/granite-3-3-8b-instruct"
    # Bu süre içinde yanıt gelmezse kural tabanlı karar kullanılır (saniye)
    watsonx_timeout: float = 15.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def watsonx_enabled(self) -> bool:
        return bool(self.watsonx_apikey and self.watsonx_project_id)


settings = Settings()


def yerel_simdi() -> datetime:
    """Hastanenin saat dilimindeki an (DB'ye saat dilimsiz yazılır, DB2 TIME salise tutmaz)."""
    return datetime.now(ZoneInfo(settings.timezone)).replace(tzinfo=None, microsecond=0)
