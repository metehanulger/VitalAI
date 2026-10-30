"""PostgreSQL schema, migration, and data-access behavior."""

import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, select

from app.db import crud
from app.db.database import Base, SessionLocal, engine
from app.db.tables import HastalikSevk
from app.models.schemas import TriajIstek


def test_modeller_ve_migrationlar_uyumlu():
    """Alembic finds nothing to generate when the models match the migrated schema."""
    with engine.connect() as conn:
        farklar = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert farklar == []


def test_referans_verisi_yuklenir():
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(HastalikSevk)) == 15
        assert crud.semptoma_gore_sevk_ara(db, "CHEST")


@pytest.mark.parametrize(("alan", "deger"), [("spo2", 35), ("nabiz", 280)])
def test_kritik_vital_degerleri_kaydedilir(client, istek, alan, deger):
    """Extreme but valid vitals must be stored, not rejected by a database constraint."""
    istek["vitaller"][alan] = deger
    r = client.post("/api/triage", json=istek)
    assert r.status_code == 201, r.text
    assert r.json()["hasta_durumu"] == "KIRMIZI"


def test_es_zamanli_kayitlar_benzersiz_sira_no_alir(istek):
    """Concurrent inserts for the same day get distinct, consecutive queue numbers."""
    zaman = datetime(2030, 1, 15, 9, 30)
    triaj_istek = TriajIstek.model_validate(istek)
    karar = SimpleNamespace(durum="YESIL", risk_skoru=5, birim_uyumluluk_siralamasi=[], karar_kaynagi="KURAL")

    def kaydet(_):
        with SessionLocal() as db:
            return crud.triaj_kaydi_olustur(db, triaj_istek, karar, zaman).sira_no

    with ThreadPoolExecutor(max_workers=8) as havuz:
        numaralar = list(havuz.map(kaydet, range(16)))
    assert sorted(numaralar) == list(range(1, 17))


def test_birim_uyumlulugu_jsonb_olarak_saklanir(istek):
    triaj_istek = TriajIstek.model_validate(istek)
    birimler = [{"birim": "Cardiology", "uyum_skoru": 0.9, "gerekce": "Göğüs ağrısı"}]
    karar = SimpleNamespace(durum="SARI", risk_skoru=3, birim_uyumluluk_siralamasi=birimler)
    with SessionLocal() as db:
        log = crud.triaj_kaydi_olustur(db, triaj_istek, karar, datetime(2030, 2, 1, 10, 0))
        assert log.birim_uyumluluk_json == birimler
        assert log.created_at is not None and log.created_at.tzinfo is not None


def test_gecmis_sayfalanir(client, istek):
    for _ in range(3):
        client.post("/api/triage", json=copy.deepcopy(istek))
    r = client.get("/api/triage/history", params={"limit": 2})
    assert r.status_code == 200
    toplam = int(r.headers["X-Total-Count"])
    assert len(r.json()) == 2 and toplam >= 3

    ikinci = client.get("/api/triage/history", params={"limit": 2, "offset": 2}).json()
    assert {k["log_id"] for k in ikinci}.isdisjoint({k["log_id"] for k in r.json()})


def test_gecmis_limit_siniri(client):
    assert client.get("/api/triage/history", params={"limit": 501}).status_code == 422


_URGENCY_ARTIFACT = Path(__file__).resolve().parents[1] / "model_artifacts" / "urgency.joblib"


@pytest.mark.skipif(not _URGENCY_ARTIFACT.is_file(), reason="trained urgency model is not available")
def test_aciliyet_tahmini_predict_ile_ayni(istek):
    """The single predict_proba path returns the same class as the pipeline's predict."""
    from app.models.ml import UrgencyClassifier, _feature_frame
    from app.models.schema import PatientIntake

    model = UrgencyClassifier.load(str(_URGENCY_ARTIFACT))
    assert model.pipeline.named_steps["classifier"].n_jobs == 1
    for spo2, sikayet in [(98, "Boğaz ağrısı"), (84, "Göğüs ağrısı ve nefes darlığı"), (92, "Karın ağrısı")]:
        veri = copy.deepcopy(istek)
        veri["vitaller"]["spo2"] = spo2
        veri["sikayet"]["ana_sikayet"] = sikayet
        intake = PatientIntake.from_mapping(veri)
        beklenen = int(model.pipeline.predict(_feature_frame([intake.to_dict()]))[0])
        assert model.predict(intake).urgency_level == beklenen
