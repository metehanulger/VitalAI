"""Triage output quality: prompt content, negation, departments, and ML inputs."""

import importlib
import io
import json
import urllib.error
from types import SimpleNamespace

import pytest

from app.core import triage
from app.core.poliklinikler import ACIL_SERVIS, poliklinik_esle, poliklinik_listesi
from app.core.prompts import (
    SIKAYET_NORMALIZASYON_ISTEMI,
    build_full_triage_prompt,
    triaj_json_semasi,
    triaj_sistem_istemi,
)
from app.models.ml import SpecialtyCandidate, SpecialtyPrediction, TriagePrediction
from app.models.schemas import TriajIstek

llm_modulu = importlib.import_module("app.core.llm_client")


# --- Prompt ---------------------------------------------------------------------

def test_istem_diyastolik_tansiyonu_icerir(istek):
    metin = build_full_triage_prompt(TriajIstek.model_validate(istek))
    assert "Blood pressure: 120/80 mmHg" in metin


def test_ana_istem_kullanici_mesajinda_tekrarlanmaz(istek):
    metin = build_full_triage_prompt(TriajIstek.model_validate(istek))
    assert "TRIAGE CATEGORIES" not in metin
    assert "TRIAGE CATEGORIES" in triaj_sistem_istemi()


def test_sistem_istemi_ve_sema_poliklinik_listesini_kullanir():
    liste = list(poliklinik_listesi())
    assert ", ".join(liste) in triaj_sistem_istemi()
    sema = triaj_json_semasi()
    assert sema["properties"]["onerilen_poliklinik"]["enum"] == liste
    assert sema["properties"]["birim_uyumluluk_siralamasi"]["items"]["properties"]["birim"]["enum"] == liste
    assert list(sema["properties"])[0] == "degerlendirme"


# --- Negation in the rules ------------------------------------------------------

@pytest.mark.parametrize(
    ("sikayet", "beklenen"),
    [
        ("Göğüs ağrısı yok, sadece öksürük", "YESIL"),
        ("No chest pain, mild cough", "YESIL"),
        ("Patient denies chest pain", "YESIL"),
        ("Kanaması olmadı, dizim sıyrıldı", "YESIL"),
        ("Bilinç kaybı yok, başım dönüyor", "YESIL"),
        ("Göğüs ağrısı var ama ateş yok", "SARI"),
        ("Nefes darlığı yok ama göğüs ağrısı var", "SARI"),
        # Not sure the negation covers both symptoms, so the rule stays cautious.
        ("Göğüs ağrısı ve nefes darlığı yok", "SARI"),
        ("Bayılma hissi var", "SARI"),
        ("İki gündür burnum akıyor ve hapşırıyorum", "YESIL"),
        ("Elimi ocakta yaktım, burns on my hand", "SARI"),
        ("Patient fractured his wrist", "SARI"),
        ("Nefes alamıyorum", "KIRMIZI"),
        ("Babam inme geçirdi, konuşamıyor", "KIRMIZI"),
    ],
)
def test_olumsuzlanan_belirti_kural_tetiklemez(istek, sikayet, beklenen):
    istek["sikayet"]["ana_sikayet"] = sikayet
    assert triage.kural_tabanli_degerlendir(TriajIstek.model_validate(istek))[0] == beklenen


# --- Departments ----------------------------------------------------------------

@pytest.mark.parametrize(
    ("ad", "beklenen"),
    [
        ("Cardiology", "Cardiology"),
        ("ENT", "Otolaryngology"),
        ("orthopedics", "Orthopedics and Traumatology"),
        ("Cardiovascular / Pulmonary", "Cardiology"),
        ("Kardiyoloji", "Cardiology"),
        ("Gastroenterolgy", "Gastroenterology"),
        ("Radiology", None),
        ("Letters", None),
        ("", None),
        (None, None),
    ],
)
def test_poliklinik_esleme(ad, beklenen):
    assert poliklinik_esle(ad) == beklenen


def test_ml_uzmanliklari_eslenir_ve_birlesir():
    ham = SpecialtyPrediction([
        SpecialtyCandidate("Neurology", 0.30),
        SpecialtyCandidate("Radiology", 0.20),
        SpecialtyCandidate("Surgery", 0.15),
        SpecialtyCandidate("Bariatrics", 0.10),
    ])
    sonuc = triage._uzmanliklari_eslestir(ham)
    assert [(c.specialty, round(c.confidence, 2)) for c in sonuc.candidates] == [
        ("Neurology", 0.30),
        ("General Surgery", 0.25),
    ]


def test_llm_liste_disi_poliklinigi_duzeltilir(istek, monkeypatch):
    monkeypatch.setattr(triage.llm_client, "generate", lambda *a, **k: {
        "durum": "SARI",
        "risk_skoru": 3,
        "onerilen_poliklinik": "Radiology",
        "birim_uyumluluk_siralamasi": [
            {"birim": "Radiology", "uyum_skoru": 0.9, "gerekce": "Imaging"},
            {"birim": "ENT", "uyum_skoru": 1.7, "gerekce": "Throat"},
            {"birim": "Otolaryngology", "uyum_skoru": 0.4, "gerekce": "Duplicate"},
        ],
    })
    karar = triage.triaj_karari_ver(TriajIstek.model_validate(istek))
    assert karar.onerilen_poliklinik == "Otolaryngology"
    assert [(b.birim, b.uyum_skoru) for b in karar.birim_uyumluluk_siralamasi] == [("Otolaryngology", 1.0)]


def test_llm_departman_vermezse_acil_servis(istek, monkeypatch):
    monkeypatch.setattr(triage.llm_client, "generate", lambda *a, **k: {"durum": "YESIL", "risk_skoru": 5})
    assert triage.triaj_karari_ver(TriajIstek.model_validate(istek)).onerilen_poliklinik == ACIL_SERVIS


def test_istek_sema_ve_referans_tablosuyla_gonderilir(client, istek, monkeypatch):
    cagrilar = []

    def sahte(prompt, system_prompt=None, **kwargs):
        cagrilar.append((prompt, system_prompt, kwargs))
        return {"durum": "YESIL", "risk_skoru": 4, "onerilen_poliklinik": "Otolaryngology"}

    monkeypatch.setattr(triage.llm_client, "generate", sahte)
    r = client.post("/api/triage", json=istek)
    assert r.status_code == 201, r.text
    assert r.json()["onerilen_poliklinik"] == "Otolaryngology"

    prompt, system_prompt, kwargs = cagrilar[-1]
    assert system_prompt == triaj_sistem_istemi()
    assert kwargs["json_schema"] == triaj_json_semasi()
    assert "HOSPITAL REFERRAL REFERENCE" in prompt and "Acute appendicitis" in prompt
    # Default triage codes from the reference table are not shown to the LLM.
    assert "KIRMIZI" not in prompt.split("HOSPITAL REFERRAL REFERENCE")[1]


# --- ML inputs ------------------------------------------------------------------

class _SahteAciliyet:
    def __init__(self):
        self.girdiler = []

    def predict(self, intake):
        self.girdiler.append(intake)
        return TriagePrediction(urgency_level=4, urgency_label="Urgent", confidence=0.9, probabilities={4: 0.9})


class _SahteUzmanlik:
    pipeline = SimpleNamespace(classes_=["Neurology", "Radiology", "Surgery"])

    def __init__(self):
        self.metinler = []

    def predict(self, metin, top_k=3):
        self.metinler.append((metin, top_k))
        return SpecialtyPrediction([
            SpecialtyCandidate("Radiology", 0.5),
            SpecialtyCandidate("Neurology", 0.4),
            SpecialtyCandidate("Surgery", 0.1),
        ])


@pytest.mark.parametrize(
    ("kategori", "beklenen_sikayet"),
    [("Stroke symptoms", "Stroke symptoms"), ("NONE", "My face drooped on one side and I cannot speak.")],
)
def test_ml_modelleri_normalize_sikayeti_kullanir(istek, monkeypatch, kategori, beklenen_sikayet):
    aciliyet, uzmanlik = _SahteAciliyet(), _SahteUzmanlik()
    monkeypatch.setattr(triage, "ml_modellerini_yukle", lambda: (aciliyet, uzmanlik))
    triage._sikayet_normu_onbellekli.cache_clear()
    ingilizce = "My face drooped on one side and I cannot speak."

    def sahte(prompt, system_prompt=None, **kwargs):
        if system_prompt == SIKAYET_NORMALIZASYON_ISTEMI:
            assert kwargs["json_schema"]["properties"]["complaint_category"]["enum"][-1] == "NONE"
            return {"english_text": ingilizce, "complaint_category": kategori}
        return {"durum": "SARI", "risk_skoru": 2, "onerilen_poliklinik": "Neurology"}

    monkeypatch.setattr(triage.llm_client, "generate", sahte)
    istek["sikayet"]["ana_sikayet"] = "Yüzümün bir tarafı düştü, konuşamıyorum"
    sinyaller = triage._ml_signals(TriajIstek.model_validate(istek))
    triage._sikayet_normu_onbellekli.cache_clear()

    girdi = aciliyet.girdiler[0]
    assert girdi.chief_complaint == beklenen_sikayet
    assert girdi.chronic_conditions is None and girdi.regular_medications is None
    assert uzmanlik.metinler[0] == (ingilizce, 3)
    assert [c.specialty for c in sinyaller.specialties.candidates] == ["Neurology", "General Surgery"]
    assert sinyaller.complaint_category == (None if kategori == "NONE" else kategori)


def test_llm_yoksa_ml_ham_sikayetle_calisir(istek, monkeypatch):
    aciliyet, uzmanlik = _SahteAciliyet(), _SahteUzmanlik()
    monkeypatch.setattr(triage, "ml_modellerini_yukle", lambda: (aciliyet, uzmanlik))
    monkeypatch.setattr(triage.llm_client, "generate", lambda *a, **k: None)
    triage._sikayet_normu_onbellekli.cache_clear()
    triage._ml_signals(TriajIstek.model_validate(istek))
    assert aciliyet.girdiler[0].chief_complaint == istek["sikayet"]["ana_sikayet"]


# --- Structured output fallback -------------------------------------------------

class _Yanit(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_openai_sema_reddedilirse_json_moduna_doner(monkeypatch):
    gonderilen = []

    def sahte_urlopen(req, timeout=None):
        govde = json.loads(req.data)
        gonderilen.append(govde["response_format"]["type"])
        if govde["response_format"]["type"] == "json_schema":
            raise urllib.error.HTTPError(req.full_url, 400, "bad", {}, io.BytesIO(b"unsupported"))
        icerik = json.dumps({"choices": [{"message": {"content": '{"durum": "SARI"}'}}]})
        return _Yanit(icerik.encode())

    monkeypatch.setattr(llm_modulu.urllib.request, "urlopen", sahte_urlopen)
    istemci = llm_modulu.UniversalLLMClient(api_key="k", base_url="https://example.test/v1", provider="openai_compatible")
    sema = {"type": "object", "properties": {}}
    assert istemci.generate("x", "y", json_schema=sema) == {"durum": "SARI"}
    assert istemci.generate("x", "y", json_schema=sema) == {"durum": "SARI"}
    assert gonderilen == ["json_schema", "json_object", "json_object"]


def test_gemini_sema_reddedilirse_semasiz_tekrar_dener(monkeypatch):
    monkeypatch.setattr(llm_modulu.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(llm_modulu.settings, "LLM_API_KEY", "")
    istemci = llm_modulu.UniversalLLMClient()
    semalar = []

    class _Hata(Exception):
        code = 400

    def generate_content(**kwargs):
        semalar.append(kwargs["config"].response_json_schema)
        if kwargs["config"].response_json_schema is not None:
            raise _Hata("schema not supported")
        return SimpleNamespace(text='{"durum": "YESIL"}')

    istemci._gemini_client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    sema = {"type": "object", "properties": {"durum": {"type": "string"}}}
    assert istemci.generate("x", "y", json_schema=sema) == {"durum": "YESIL"}
    assert semalar == [sema, None]
