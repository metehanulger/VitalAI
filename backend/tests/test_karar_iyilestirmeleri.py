"""Decision quality: NEWS2 inputs, keyword rules, routing, storage, and LLM fallbacks."""

import copy
import importlib
from datetime import datetime
from types import SimpleNamespace

import pytest

from app.core import triage
from app.core.anahtar_kelime import desen, terim_var
from app.core.metin import katla
from app.core.poliklinikler import ACIL_SERVIS, sikayetten_poliklinik
from app.db import crud
from app.db.database import SessionLocal
from app.db.tables import HastaneLog
from app.evaluation.degerlendir import VakaSonucu, metrikler, satiri_istege_cevir
from app.models.schemas import TriajIstek

llm_modulu = importlib.import_module("app.core.llm_client")


def _istek(istek, **vitaller):
    veri = copy.deepcopy(istek)
    veri["vitaller"].update(vitaller)
    return TriajIstek.model_validate(veri)


@pytest.fixture
def llm_yok(monkeypatch):
    monkeypatch.setattr(triage.llm_client, "generate", lambda *a, **k: None)


# --- NEWS2 and consciousness ----------------------------------------------------

def test_news2_bilinc_ve_ek_oksijen(istek):
    assert triage.news2_hesapla(_istek(istek).vitaller) == (0, [])
    assert triage.news2_hesapla(_istek(istek, ek_oksijen=True).vitaller) == (2, [])
    assert triage.news2_hesapla(_istek(istek, bilinc="c").vitaller) == (3, ["Consciousness"])


@pytest.mark.parametrize("bilinc", ["P", "U"])
def test_agriya_yanit_veya_yanitsiz_hasta_kirmizi(istek, bilinc):
    durum, gerekce, _ = triage.kural_tabanli_degerlendir(_istek(istek, bilinc=bilinc))
    assert durum == "KIRMIZI" and "AVPU" in gerekce


def test_gecersiz_bilinc_degeri_reddedilir(client, istek):
    istek["vitaller"]["bilinc"] = "X"
    assert client.post("/api/triage", json=istek).status_code == 422


def test_bilinc_ve_oksijen_kaydedilir_ve_doner(client, istek, llm_yok):
    istek["vitaller"].update(bilinc="V", ek_oksijen=True)
    veri = client.post("/api/triage", json=istek).json()
    assert veri["hasta_durumu"] == "KIRMIZI"
    assert veri["news2_skoru"] == 5
    detay = client.get(f"/api/triage/{veri['log_id']}").json()
    assert (detay["vitaller"]["bilinc"], detay["vitaller"]["ek_oksijen"]) == ("V", True)


def test_istem_news2_ve_bilinci_icerir(istek):
    i = _istek(istek, bilinc="C", ek_oksijen=True)
    metin = triage.build_full_triage_prompt(i, news2=triage.news2_hesapla(i.vitaller))
    assert "Consciousness (ACVPU): C (new confusion)" in metin
    assert "Supplemental oxygen: yes" in metin
    assert "CALCULATED NEWS2 SCORE: 5 (parameters scoring 3: Consciousness)" in metin
    assert "older than 64" in triage.triaj_sistem_istemi()


# --- Keyword rules ----------------------------------------------------------------

@pytest.mark.parametrize(
    ("sikayet", "beklenen"),
    [
        ("Otobüsten inmeye çalışırken düştüm, dizim sıyrıldı", "YESIL"),
        ("Nöbetçi eczaneye gittim, boğazım ağrıyor", "YESIL"),
        ("Bayılmadım ama başım dönüyor", "YESIL"),
        ("Bir saattir sağ kolum güçsüz, konuşmam peltekleşti", "SARI"),
        ("Karnım çok ağrıyor", "SARI"),
        ("Nefesim daralıyor", "SARI"),
        ("Sabah kan kustum", "SARI"),
        ("Dilim ve dudaklarım şişiyor", "SARI"),
        ("Babam tepki vermiyor", "KIRMIZI"),
        ("Gebeliğim 30 haftalık, karnım sertleşiyor", "SARI"),
    ],
)
def test_turkce_anahtar_kelimeler(istek, sikayet, beklenen):
    istek["sikayet"]["ana_sikayet"] = sikayet
    assert triage.kural_tabanli_degerlendir(TriajIstek.model_validate(istek))[0] == beklenen


def test_ingilizce_kelime_tam_eslesir():
    d = desen([], ["burn"])
    assert terim_var("burns on my hand", d) and terim_var("i burned it", d)
    assert not terim_var(katla("burnum akıyor"), d)


# --- Department routing when the LLM is unavailable ----------------------------

@pytest.mark.parametrize(
    ("sikayet", "beklenen"),
    [
        ("Üç gündür idrar yaparken yanma", "Urology"),
        ("Sol gözümde bulanık görme", "Ophthalmology"),
        ("Merdivenden düştüm, bileğim şişti", "Orthopedics and Traumatology"),
        ("Sağ alt karnımda artan ağrı ve bulantı", "General Surgery"),
        ("Göğüs ağrım yok, burnum akıyor", "Otolaryngology"),
        ("Kollarımda kaşıntılı döküntü", "Dermatology"),
        ("Dişim çok ağrıyor", "Dentistry"),
        ("Hiçbir şikayeti yok, kontrol için geldi", None),
    ],
)
def test_sikayetten_poliklinik(sikayet, beklenen):
    assert sikayetten_poliklinik(katla(sikayet)) == beklenen


def test_llm_yokken_yonlendirici_kullanilir(istek, llm_yok):
    istek["sikayet"]["ana_sikayet"] = "Sol gözümde bulanık görme ve sulanma"
    karar = triage.triaj_karari_ver(TriajIstek.model_validate(istek))
    assert karar.onerilen_poliklinik == "Ophthalmology"
    assert karar.karar_kaynagi == "KURAL"


def test_llm_yokken_kirmizi_hasta_acil_serviste_kalir(istek, llm_yok):
    istek["sikayet"]["ana_sikayet"] = "Gözümde ağrı var"
    karar = triage.triaj_karari_ver(_istek(istek, spo2=85))
    assert (karar.durum, karar.onerilen_poliklinik) == ("KIRMIZI", ACIL_SERVIS)


# --- Storage --------------------------------------------------------------------

def test_uzun_llm_metinleri_kirpilir(istek):
    karar = SimpleNamespace(
        durum="SARI", risk_skoru=3, birim_uyumluluk_siralamasi=[],
        onerilen_poliklinik="Cardiology" * 30, kritik_bulgu="k" * 5000,
        erken_uyari_notu="e" * 5000, aciklama="a" * 5000, karar_kaynagi="GEMINI+ML+KURAL",
    )
    kolon = HastaneLog.__table__.c
    with SessionLocal() as db:
        log = crud.triaj_kaydi_olustur(db, TriajIstek.model_validate(istek), karar, datetime(2030, 3, 1, 8, 0))
        assert len(log.aciklama) == kolon.aciklama.type.length
        assert len(log.kritik_bulgu) == kolon.kritik_bulgu.type.length
        assert len(log.onerilen_poliklinik) == kolon.onerilen_poliklinik.type.length


@pytest.mark.parametrize(
    ("ilk_esi", "yeni_durum", "beklenen_esi"),
    [(5, "SARI", 3), (5, "KIRMIZI", 1), (1, "SARI", 2), (3, "YESIL", 4), (2, "SARI", 2)],
)
def test_elle_durum_guncellemesi_esiyi_uyumlu_yapar(istek, ilk_esi, yeni_durum, beklenen_esi):
    durumlar = {1: "KIRMIZI", 2: "SARI", 3: "SARI", 4: "YESIL", 5: "YESIL"}
    karar = SimpleNamespace(durum=durumlar[ilk_esi], risk_skoru=ilk_esi, birim_uyumluluk_siralamasi=[])
    with SessionLocal() as db:
        log = crud.triaj_kaydi_olustur(db, TriajIstek.model_validate(istek), karar, datetime(2030, 4, 1, 8, 0))
        log = crud.durum_guncelle(db, log, yeni_durum)
        assert (log.durum, log.risk_skoru) == (yeni_durum, beklenen_esi)


def test_api_yaniti_llm_bulgularini_icerir(client, istek, monkeypatch):
    monkeypatch.setattr(triage.llm_client, "generate", lambda *a, **k: {
        "durum": "SARI", "risk_skoru": 3, "onerilen_poliklinik": "Otolaryngology",
        "birim_uyumluluk_siralamasi": [
            {"birim": "Otolaryngology", "uyum_skoru": 0.9, "gerekce": "Throat"},
            {"birim": "Internal Medicine", "uyum_skoru": 0.3, "gerekce": "General"},
        ],
        "kritik_bulgu": "Odynophagia", "erken_uyari_notu": "Watch for stridor",
    })
    veri = client.post("/api/triage", json=istek).json()
    assert veri["kritik_bulgu"] == "Odynophagia"
    assert veri["erken_uyari_notu"] == "Watch for stridor"
    assert veri["news2_skoru"] == 0
    assert [b["birim"] for b in veri["birim_uyumluluk_siralamasi"]] == ["Otolaryngology", "Internal Medicine"]


# --- Gemini fallback models -------------------------------------------------------

class _ApiHatasi(Exception):
    def __init__(self, code, mesaj="error"):
        super().__init__(mesaj)
        self.code = code


def _gemini_istemcisi(monkeypatch, davranislar):
    monkeypatch.setattr(llm_modulu.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(llm_modulu.settings, "LLM_API_KEY", "")
    monkeypatch.setattr(llm_modulu.settings, "GEMINI_MODEL", "birincil")
    monkeypatch.setattr(llm_modulu.settings, "GEMINI_FALLBACK_MODELS", "yedek1, yedek2")
    istemci = llm_modulu.UniversalLLMClient()
    cagrilar = []

    def generate_content(model, **kwargs):
        cagrilar.append(model)
        davranis = davranislar.get(model)
        if isinstance(davranis, Exception):
            raise davranis
        return SimpleNamespace(text=davranis)

    istemci._gemini_client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    return istemci, cagrilar


def test_gemini_kota_dolunca_yedek_modele_gecer_ve_bekletir(monkeypatch):
    istemci, cagrilar = _gemini_istemcisi(monkeypatch, {
        "birincil": _ApiHatasi(429, "Generate content requests per day limit exceeded"),
        "yedek1": '{"durum": "SARI"}',
    })
    assert istemci.generate("x", "y") == {"durum": "SARI"}
    assert istemci.generate("x", "y") == {"durum": "SARI"}
    # The primary model is skipped on the second call because it is cooling down.
    assert cagrilar == ["birincil", "yedek1", "yedek1"]


def test_gemini_json_olmayan_yanitta_sonraki_modeli_dener(monkeypatch):
    istemci, cagrilar = _gemini_istemcisi(monkeypatch, {
        "birincil": "no json here",
        "yedek1": _ApiHatasi(404),
        "yedek2": '{"durum": "YESIL"}',
    })
    assert istemci.generate("x", "y") == {"durum": "YESIL"}
    assert cagrilar == ["birincil", "yedek1", "yedek2"]


def test_gemini_tum_modeller_basarisizsa_none(monkeypatch):
    istemci, _ = _gemini_istemcisi(monkeypatch, {m: _ApiHatasi(503) for m in ("birincil", "yedek1", "yedek2")})
    assert istemci.generate("x", "y") is None


# --- Evaluation script ----------------------------------------------------------

def test_degerlendirme_metrikleri():
    def s(beklenen, tahmin, bp="Cardiology", tp="Cardiology", ilk3=("Cardiology",), kaynak="GEMINI+KURAL"):
        return VakaSonucu("v", beklenen, tahmin, bp, tp, list(ilk3), kaynak, 1.0)

    m = metrikler([
        s("KIRMIZI", "SARI"),
        s("YESIL", "SARI", tp="Neurology", ilk3=("Neurology", "Cardiology")),
        s("SARI", "SARI", kaynak="KURAL"),
        s("YESIL", "YESIL", tp="Urology", ilk3=("Urology",)),
    ])
    assert (m["dusuk_triyaj"], m["yuksek_triyaj"], m["durum_dogrulugu"]) == (0.25, 0.25, 0.5)
    assert (m["poliklinik_ilk1"], m["poliklinik_ilk3"], m["llm_kullanildi"]) == (0.5, 0.75, 0.75)


def test_degerlendirme_satiri_gecerli_istek_uretir():
    satir = {
        "yas": "70", "kronik_rahatsizlik": "", "surekli_ilac": "", "nabiz": "90", "tansiyon_sistolik": "130",
        "tansiyon_diastolik": "80", "solunum": "18", "ates": "37.0", "spo2": "95", "bilinc": "c",
        "ek_oksijen": "evet", "ana_sikayet": "Öksürük", "agri_skalasi": "2",
    }
    istek = TriajIstek.model_validate(satiri_istege_cevir(satir))
    assert (istek.vitaller.bilinc, istek.vitaller.ek_oksijen, istek.tibbi_gecmis.kronik_rahatsizlik) == ("C", True, None)
