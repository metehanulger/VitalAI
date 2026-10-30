import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="vitialai-tests-")
# Tests drop and recreate every table, so they need a dedicated PostgreSQL database.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+psycopg://triaj:triaj_sifre@localhost:5432/triajdb_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["DB_AUTO_MIGRATE"] = "true"
os.environ["LLM_PROVIDER"] = "openai_compatible"
os.environ["LLM_API_KEY"] = ""
os.environ["LLM_BASE_URL"] = "https://api.openai.com/v1"
os.environ["GEMINI_API_KEY"] = ""
os.environ["WATSONX_API_KEY"] = ""
os.environ["WATSONX_PROJECT_ID"] = ""
os.environ["TRIAGE_URGENCY_MODEL"] = os.path.join(_TEST_DIR, "no-urgency-model.joblib")
os.environ["TRIAGE_SPECIALTY_MODEL"] = os.path.join(_TEST_DIR, "no-specialty-model.joblib")

import pytest
from fastapi.testclient import TestClient

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db.database import Base, engine
from app.db.migrate import upgrade_to_head
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def temiz_veritabani():
    """Rebuild the dedicated test database from the Alembic migrations each session."""
    db_adi = make_url(TEST_DATABASE_URL).database or ""
    if "test" not in db_adi.lower():
        pytest.exit(f"Refusing to reset '{db_adi}': TEST_DATABASE_URL must name a test database.", returncode=2)
    from app.db import tables  # noqa: F401  (register models on Base.metadata)
    with engine.begin() as conn:
        Base.metadata.drop_all(bind=conn)
        conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
    upgrade_to_head()
    yield
    engine.dispose()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def istek():
    """Vitalleri normal, acil olmayan bir hasta."""
    return {
        "demografi": {
            "isim": "Ayşe Yılmaz",
            "yas": 34,
            "boy": 165,
            "kilo": 60.5,
            "kan_grubu": "A+",
            "kimlik_turu": "TC",
            "kimlik_no": "10000000146",
        },
        "tibbi_gecmis": {"kronik_rahatsizlik": "Astım", "surekli_ilac": ""},
        "vitaller": {
            "nabiz": 78,
            "tansiyon_sistolik": 120,
            "tansiyon_diastolik": 80,
            "solunum": 16,
            "ates": 36.8,
            "spo2": 98,
        },
        "sikayet": {"ana_sikayet": "Boğaz ağrısı ve hafif öksürük", "agri_skalasi": 3},
    }
