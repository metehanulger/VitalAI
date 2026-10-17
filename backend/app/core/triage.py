"""Acil Servis Ön Triaj Karar Motoru (Evrensel LLM İstemcisi + NEWS2 / Klinik Kural Güvencesi).

Bu modül:
1. 4 Kart verisini Master Prompt ile işler (Dilediğiniz herhangi bir LLM: OpenAI, DeepSeek, Groq, Gemini, Watsonx, Ollama vb.).
2. Vitallerden NEWS2 klinik bozulma skorunu hesaplar.
3. Kural ve AI sonucunu birleştirir; AI, kuralın belirlediği aciliyeti asla düşüremez (Güvenlik Kalkanı).
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Optional, List, Any

from app.core.prompts import build_full_triage_prompt, MASTER_TRIAGE_PROMPT
from app.core.llm_client import llm_client

logger = logging.getLogger(__name__)

SEVIYELER = ("YESIL", "SARI", "KIRMIZI")  # Artan aciliyet indeksi (0, 1, 2)

KRITIK_KELIMELER = [
    "bilinc kaybi", "bilinci kapali", "bayildi ve uyanmiyor", "nefes alamiyor", "nefes alamiyorum",
    "solunum durmasi", "kalp durmasi", "gogus agrisi", "gogsumde agri", "felc", "inme",
    "konusamiyor", "nobet", "havale", "siddetli kanama", "intihar", "zehirlen", "anafilaksi",
]

ACIL_KELIMELER = [
    "nefes darligi", "kanama", "kirik", "bayil", "carpinti", "kusma", "karin agrisi",
    "yuksek ates", "hamile", "gebe", "yanik", "kafa travmasi", "basini carpti",
]


@dataclass
class BirimUyumDetay:
    birim: str
    uyum_skoru: float
    gerekce: str

    def model_dump(self):
        return {"birim": self.birim, "uyum_skoru": self.uyum_skoru, "gerekce": self.gerekce}


@dataclass
class TriajKarari:
    durum: str  # KIRMIZI, SARI, YESIL
    risk_skoru: int  # 1-5 (ESI Seviyesi)
    onerilen_poliklinik: str
    birim_uyumluluk_siralamasi: List[Any] = field(default_factory=list)
    kritik_bulgu: str = ""
    erken_uyari_notu: str = ""
    aciklama: str = ""
    karar_kaynagi: str = "LLM"
    news2_skoru: int = 0


def _seviye(durum: str) -> int:
    durum = str(durum).upper()
    return SEVIYELER.index(durum) if durum in SEVIYELER else 0


def _en_acil(*durumlar: str) -> str:
    return max(durumlar, key=_seviye)


def news2_hesapla(vitaller: Any) -> tuple[int, list[str]]:
    """İngiltere Royal College of Physicians NEWS2 skorunu hesaplar."""
    def _v(key, default):
        if hasattr(vitaller, key):
            return getattr(vitaller, key)
        elif isinstance(vitaller, dict):
            return vitaller.get(key, default)
        return default

    solunum = int(_v("solunum", 16))
    spo2 = int(_v("spo2", 98))
    sistolik = int(_v("tansiyon_sistolik", 120))
    nabiz = int(_v("nabiz", 80))
    ates = float(_v("ates", 36.8))

    puanlar = {
        "Solunum": 3 if solunum <= 8 else 1 if solunum <= 11 else 0 if solunum <= 20 else 2 if solunum <= 24 else 3,
        "SpO2": 3 if spo2 <= 91 else 2 if spo2 <= 93 else 1 if spo2 <= 95 else 0,
        "Sistolik": 3 if sistolik <= 90 else 2 if sistolik <= 100 else 1 if sistolik <= 110 else 0 if sistolik <= 219 else 3,
        "Nabız": 3 if nabiz <= 40 else 1 if nabiz <= 50 else 0 if nabiz <= 90 else 1 if nabiz <= 110 else 2 if nabiz <= 130 else 3,
        "Ateş": 3 if ates <= 35.0 else 1 if ates <= 36.0 else 0 if ates <= 38.0 else 1 if ates <= 39.0 else 2,
    }

    toplam = sum(puanlar.values())
    kritikler = [param for param, p in puanlar.items() if p == 3]
    return toplam, kritikler


def kural_tabanli_degerlendir(istek: Any) -> tuple[str, str, int]:
    """Çevrimdışı deterministik klinik kural motoru."""
    vitaller = getattr(istek, "vitaller", istek)
    sikayet = getattr(istek, "sikayet", istek)

    toplam_news, kritikler = news2_hesapla(vitaller)

    ana_sikayet = ""
    agri = 1
    if hasattr(sikayet, "ana_sikayet"):
        ana_sikayet = str(sikayet.ana_sikayet).lower()
        agri = getattr(sikayet, "agri_skalasi", 1)
    elif isinstance(sikayet, dict):
        ana_sikayet = str(sikayet.get("ana_sikayet", "")).lower()
        agri = int(sikayet.get("agri_skalasi", 1))

    # 1. Kırmızı Kuralı: NEWS2 >= 7 veya tek parametre 3 puan veya kritik kelime
    for kelime in KRITIK_KELIMELER:
        if re.search(r"\b" + re.escape(kelime), ana_sikayet):
            return "KIRMIZI", f"Kritik bulgu saptandı: '{kelime}'.", toplam_news

    if toplam_news >= 7 or len(kritikler) >= 1:
        return "KIRMIZI", f"NEWS2 skoru kritik ({toplam_news}). Kritik parametreler: {', '.join(kritikler)}", toplam_news

    # 2. Sarı Kuralı: NEWS2 5-6 veya şiddetli ağrı (>=7) veya acil kelime
    if toplam_news >= 5:
        return "SARI", f"Orta derece vital bozulma (NEWS2: {toplam_news}).", toplam_news

    if agri >= 7:
        return "SARI", f"Şiddetli ağrı seviyesi ({agri}/10).", toplam_news

    for kelime in ACIL_KELIMELER:
        if re.search(r"\b" + re.escape(kelime), ana_sikayet):
            return "SARI", f"Acil semptom şüphesi: '{kelime}'.", toplam_news

    return "YESIL", "Vital bulgular stabil, acil risk saptanmadı.", toplam_news


def triaj_karari_ver(istek: Any) -> TriajKarari:
    """Master Prompt ve Evrensel LLM İstemcisini birleştirerek kesin triaj kararını üretir.
    
    FastAPI uç noktasından (api/triage.py) doğrudan çağrılır:
        karar = triaj_karari_ver(istek)
    """
    # 1. Çevrimdışı Kural Değerlendirmesi
    kural_durum, kural_gerekce, news_skor = kural_tabanli_degerlendir(istek)

    # 2. Master Prompt'u Hazırla
    tam_prompt = build_full_triage_prompt(istek)

    # 3. Evrensel LLM Çağrısı (Herhangi bir OpenAI-uyumlu API, DeepSeek, Groq, Ollama, Gemini veya Watsonx)
    ai_cikti = llm_client.generate(tam_prompt, MASTER_TRIAGE_PROMPT)
    kaynak = llm_client.provider.upper() if ai_cikti else "KURAL"

    # 4. Sonuçları Birleştir
    if ai_cikti:
        ai_durum = str(ai_cikti.get("durum", "SARI")).upper()
        # Güvenlik Kalkanı: Kural KIRMIZI diyorsa AI bunu YESIL yapamaz!
        kesin_durum = _en_acil(kural_durum, ai_durum)

        birimler_raw = ai_cikti.get("birim_uyumluluk_siralamasi", [])
        birimler = []
        for b in birimler_raw:
            birimler.append(BirimUyumDetay(
                birim=b.get("birim", "Acil Tıp"),
                uyum_skoru=float(b.get("uyum_skoru", 0.5)),
                gerekce=b.get("gerekce", "")
            ))

        return TriajKarari(
            durum=kesin_durum,
            risk_skoru=int(ai_cikti.get("risk_skoru", 2 if kesin_durum == "SARI" else (1 if kesin_durum == "KIRMIZI" else 4))),
            onerilen_poliklinik=ai_cikti.get("onerilen_poliklinik", "Acil Tıp"),
            birim_uyumluluk_siralamasi=birimler,
            kritik_bulgu=ai_cikti.get("kritik_bulgu", kural_gerekce),
            erken_uyari_notu=ai_cikti.get("erken_uyari_notu", "Hastanın vital bulgularını yakından takip ediniz."),
            aciklama=ai_cikti.get("aciklama", kural_gerekce),
            karar_kaynagi=f"{kaynak}+KURAL" if kaynak != "KURAL" else "KURAL",
            news2_skoru=news_skor,
        )

    # AI çağrısı yapılamadıysa veya API anahtarı girilmediyse güvenli kural çıktısı dön
    esi_haritasi = {"KIRMIZI": 1, "SARI": 3, "YESIL": 4}
    varsayilan_poliklinik = "Kardiyoloji" if "gogus" in str(istek).lower() else "Acil Tıp"

    return TriajKarari(
        durum=kural_durum,
        risk_skoru=esi_haritasi.get(kural_durum, 3),
        onerilen_poliklinik=varsayilan_poliklinik,
        birim_uyumluluk_siralamasi=[
            BirimUyumDetay(birim=varsayilan_poliklinik, uyum_skoru=0.85, gerekce="Belirtilen semptomlar ve kural motoru değerlendirmesi."),
            BirimUyumDetay(birim="Genel Dahiliye", uyum_skoru=0.40, gerekce="Genel medikal takip.")
        ],
        kritik_bulgu=kural_gerekce,
        erken_uyari_notu="Sistem çevrimdışı kural tabanlı değerlendirme yaptı; hekim değerlendirmesi önerilir.",
        aciklama=kural_gerekce,
        karar_kaynagi="KURAL",
        news2_skoru=news_skor,
    )
