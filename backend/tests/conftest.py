import os
import tempfile

_TEST_DIR = tempfile.mkdtemp(prefix="vitialai-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR}/test.db"
os.environ["DB_AUTO_CREATE"] = "true"
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

from app.main import app


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
