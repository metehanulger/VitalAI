import os
import tempfile

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/test.db"
os.environ["DB_AUTO_CREATE"] = "true"
os.environ["WATSONX_APIKEY"] = ""
os.environ["WATSONX_PROJECT_ID"] = ""

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
