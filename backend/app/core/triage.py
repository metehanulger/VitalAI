"""Emergency department pre-triage decision engine (LLM + NEWS2 / clinical rules).

This module:
1. Processes the four intake cards using the master prompt and configured LLM.
2. Calculates the NEWS2 clinical deterioration score from vital signs.
3. Combines rule-based and AI results; the AI cannot lower rule-based urgency.
"""

import json
import logging
from dataclasses import dataclass, field, replace
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Any

from app.core.prompts import (
    SIKAYET_NORMALIZASYON_ISTEMI,
    SIKAYET_NORMALIZASYON_SEMASI,
    build_full_triage_prompt,
    format_referans_baglami,
    triaj_json_semasi,
    triaj_sistem_istemi,
)
from app.core.llm_client import llm_client
from app.core.anahtar_kelime import desen as _desen, terim_var as _terim_var
from app.core.config import settings
from app.core.metin import katla
from app.core.poliklinikler import ACIL_SERVIS, poliklinik_esle, sikayetten_poliklinik
from app.models.ml import (
    FEDMML_COMPLAINT_CATEGORIES,
    ClinicalSpecialtyClassifier,
    SpecialtyCandidate,
    SpecialtyPrediction,
    UrgencyClassifier,
)
from app.models.schema import PatientIntake

logger = logging.getLogger(__name__)

SEVIYELER = ("YESIL", "SARI", "KIRMIZI")

# Matching rules (word starts, whole English words, negation) live in anahtar_kelime.
KRITIK_KELIMELER_TR = (
    "bilinc kaybi", "bilinci kapali", "bayildi ve uyanmiyor", "nefes alamiyor", "nefes alamiyorum",
    "solunum durmasi", "kalp durmasi", "felc", "inme",
    "konusamiyor", "nobet", "havale", "siddetli kanama", "intihar", "zehirlen", "anafilaksi",
    "tepki vermiyor", "uyandiramiyor", "nefes almiyor", "kalbi durdu",
)
KRITIK_KELIMELER_EN = (
    "loss of consciousness", "unconscious", "not breathing", "respiratory arrest", "cardiac arrest",
    "stroke", "unable to speak", "seizure", "severe bleeding", "anaphylaxis",
)
KRITIK_KELIMELER = [*KRITIK_KELIMELER_TR, *KRITIK_KELIMELER_EN]

# Turkish nouns change their stem with possessive suffixes ("karin agrisi" but
# "karnim agriyor"), so common spoken forms are listed alongside the dictionary form.
ACIL_KELIMELER_TR = (
    "nefes darligi", "nefesim daral", "nefes daral", "kanama", "kirik", "bayil", "carpinti", "kusma",
    "karin agrisi", "karnim agri", "karnim cok agri", "yuksek ates", "hamile", "gebe", "yanik",
    "kafa travmasi", "basini carpti", "basimi carpt", "gogus agrisi", "gogsumde agri", "gogsum agri",
    "gogus bask", "gogsumde bask", "gogsum sikis",
    # Possible stroke signs
    "pelteklest", "konusma bozuk", "konusmam bozul", "konusmasi bozul", "yuz kaym", "yuzum kay",
    "agzi kay", "agzim kay", "kolum gucsuz", "bacagim gucsuz", "tek tarafta gucsuz",
    # Gastrointestinal bleeding, sudden severe headache, airway swelling
    "kan kus", "kanli kus", "siyah diski", "siddetli bas agri", "en kotu bas agri", "ani bas agri",
    "dilim sis", "dudaklarim sis", "bogazim sis", "dili sis", "dudaklari sis",
)
ACIL_KELIMELER_EN = (
    "shortness of breath", "bleeding", "fracture", "fainting", "palpitations", "palpitation",
    "vomiting", "abdominal pain", "high fever", "burn", "head injury", "chest pain",
    "chest pressure", "chest tightness", "slurred speech", "facial droop", "arm weakness",
    "one-sided weakness", "vomiting blood", "black stool", "worst headache", "swollen tongue",
    "lip swelling",
)
ACIL_KELIMELER = [*ACIL_KELIMELER_TR, *ACIL_KELIMELER_EN]

_KRITIK_DESEN = _desen(KRITIK_KELIMELER_TR, KRITIK_KELIMELER_EN)
_ACIL_DESEN = _desen(ACIL_KELIMELER_TR, ACIL_KELIMELER_EN)


@dataclass
class BirimUyumDetay:
    birim: str
    uyum_skoru: float
    gerekce: str

    def model_dump(self):
        return {"birim": self.birim, "uyum_skoru": self.uyum_skoru, "gerekce": self.gerekce}


@dataclass
class TriajKarari:
    durum: str
    risk_skoru: int
    onerilen_poliklinik: str
    birim_uyumluluk_siralamasi: List[Any] = field(default_factory=list)
    kritik_bulgu: str = ""
    erken_uyari_notu: str = ""
    aciklama: str = ""
    karar_kaynagi: str = "LLM"
    news2_skoru: int = 0


@dataclass
class MLSignals:
    esi_level: int | None = None
    urgency_level: int | None = None
    urgency_confidence: float | None = None
    specialties: SpecialtyPrediction | None = None
    english_text: str | None = None
    complaint_category: str | None = None


@dataclass(frozen=True)
class SikayetNormu:
    """LLM-normalized complaint used by the English-trained ML models."""

    english_text: str
    complaint_category: str | None


@lru_cache(maxsize=1)
def ml_modellerini_yukle():
    """Load trained local model artifacts once per process (called on API startup)."""
    backend_dir = Path(__file__).resolve().parents[2]
    artifact_dir = backend_dir / "model_artifacts"

    def _artifact_path(configured: str | None, filename: str) -> Path:
        path = Path(configured) if configured else artifact_dir / filename
        return path if path.is_absolute() else backend_dir / path

    urgency_path = _artifact_path(settings.TRIAGE_URGENCY_MODEL, "urgency.joblib")
    specialty_path = _artifact_path(settings.TRIAGE_SPECIALTY_MODEL, "specialty.joblib")

    urgency_model = specialty_model = None
    if urgency_path.is_file():
        try:
            urgency_model = UrgencyClassifier.load(str(urgency_path))
        except Exception:
            logger.exception("Could not load urgency model from %s", urgency_path)
    if specialty_path.is_file():
        try:
            specialty_model = ClinicalSpecialtyClassifier.load(str(specialty_path))
        except Exception:
            logger.exception("Could not load specialty model from %s", specialty_path)
    logger.info(
        "ML models: urgency %s, specialty %s",
        "loaded" if urgency_model else "unavailable",
        "loaded" if specialty_model else "unavailable",
    )
    return urgency_model, specialty_model


class _NormalizasyonBasarisiz(Exception):
    """Raised so that failed LLM calls are not stored in the cache."""


@lru_cache(maxsize=512)
def _sikayet_normu_onbellekli(sikayet: str, gecmis: str, agri: float | None) -> SikayetNormu:
    yanit = llm_client.generate(
        json.dumps(
            {"chief_complaint": sikayet, "pain_score": agri, "medical_history": gecmis},
            ensure_ascii=False,
        ),
        SIKAYET_NORMALIZASYON_ISTEMI,
        timeout=settings.LLM_TRANSLATION_TIMEOUT_SECONDS,
        json_schema=SIKAYET_NORMALIZASYON_SEMASI,
    )
    if not yanit or not yanit.get("english_text"):
        raise _NormalizasyonBasarisiz
    kategori = yanit.get("complaint_category")
    return SikayetNormu(
        english_text=str(yanit["english_text"]),
        complaint_category=kategori if kategori in FEDMML_COMPLAINT_CATEGORIES else None,
    )


def _sikayet_normu(sikayet: str, gecmis: str, agri: float | None) -> SikayetNormu | None:
    """Translate the complaint and map it to a FedMML category in one LLM call.

    Successful results are cached in memory, so repeated complaints skip the call.
    Returns None when no LLM is available.
    """
    try:
        return _sikayet_normu_onbellekli(sikayet, gecmis, agri)
    except _NormalizasyonBasarisiz:
        return None


def _uzmanliklari_eslestir(tahmin: SpecialtyPrediction, top_k: int = 3) -> SpecialtyPrediction:
    """Map ML specialty labels onto the department list and merge their probabilities.

    Labels that are not clinics (for example Radiology) are dropped; labels that map
    to the same department (for example Surgery and Bariatrics) are summed.
    """
    birlesik: dict[str, float] = {}
    for aday in tahmin.candidates:
        bolum = poliklinik_esle(aday.specialty)
        if bolum:
            birlesik[bolum] = birlesik.get(bolum, 0.0) + aday.confidence
    sirali = sorted(birlesik.items(), key=lambda item: item[1], reverse=True)[:top_k]
    return SpecialtyPrediction([SpecialtyCandidate(specialty=b, confidence=p) for b, p in sirali])


def _ml_signals(istek: Any) -> MLSignals:
    urgency_model, specialty_model = ml_modellerini_yukle()
    if urgency_model is None and specialty_model is None:
        return MLSignals()

    values = istek.model_dump() if hasattr(istek, "model_dump") else istek
    intake = PatientIntake.from_mapping(values)
    signals = MLSignals()

    sikayet = intake.chief_complaint or ""
    gecmis = " ".join(p for p in (intake.chronic_conditions, intake.regular_medications) if p)
    normu = _sikayet_normu(sikayet, gecmis, intake.pain_score) if (sikayet or gecmis) else None
    if normu:
        signals.english_text = normu.english_text
        signals.complaint_category = normu.complaint_category

    if urgency_model is not None:
        # FedMML knows only its 28 English complaint strings and has no history columns,
        # so pass the mapped category (or the English text) and leave history empty.
        model_sikayeti = (normu.complaint_category or normu.english_text) if normu else sikayet
        prediction = urgency_model.predict(
            replace(intake, chief_complaint=model_sikayeti, chronic_conditions=None, regular_medications=None)
        )
        signals.urgency_level = prediction.urgency_level
        signals.urgency_confidence = prediction.confidence
        signals.esi_level = 6 - prediction.urgency_level

    if specialty_model is not None:
        metin = normu.english_text if normu else " ".join(p for p in (sikayet, gecmis) if p)
        sinif_sayisi = len(getattr(specialty_model.pipeline, "classes_", [])) or 3
        signals.specialties = _uzmanliklari_eslestir(specialty_model.predict(metin, top_k=sinif_sayisi))
    return signals


def _esi_for_status(status: str) -> int:
    return {"KIRMIZI": 1, "SARI": 3, "YESIL": 5}.get(str(status).upper(), 3)


def _status_for_esi(esi_level: int) -> str:
    if esi_level <= 1:
        return "KIRMIZI"
    if esi_level <= 3:
        return "SARI"
    return "YESIL"


def _valid_esi(value: Any, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed in (1, 2, 3, 4, 5) else fallback


def _esi_for_ai_decision(status: str, value: Any) -> int:
    """Keep the LLM's ESI score consistent with its color category."""
    allowed_by_status = {
        "KIRMIZI": {1},
        "SARI": {2, 3},
        "YESIL": {4, 5},
    }
    fallback = _esi_for_status(status)
    score = _valid_esi(value, fallback)
    if score not in allowed_by_status.get(status, set()):
        logger.warning("LLM returned a triage status and ESI score that do not match; using the status-based score")
        return fallback
    return score


def _apply_age_adjustment(esi_level: int, istek: Any) -> tuple[int, bool, bool]:
    """Raise displayed urgency by one for patients older than 64, capped at 5.

    Stored ``risk_skoru`` uses ESI order (1 is most urgent), while the UI's
    project scale is the reverse (1 is least urgent). Lowering ESI by one thus
    raises the displayed project urgency by one.
    """
    demographics = getattr(istek, "demografi", None)
    if demographics is None and isinstance(istek, dict):
        demographics = istek.get("demografi", {})
    age = getattr(demographics, "yas", None)
    if age is None and isinstance(demographics, dict):
        age = demographics.get("yas", demographics.get("age"))
    if age is None:
        age = getattr(istek, "age", None)

    try:
        over_64 = float(age) > 64
    except (TypeError, ValueError):
        over_64 = False
    if not over_64:
        return esi_level, False, False

    adjusted_esi = max(1, esi_level - 1)
    return adjusted_esi, True, adjusted_esi != esi_level


def _age_adjustment_note(text: Any, eligible: bool, changed: bool) -> str:
    base = str(text or "").strip()
    if not eligible:
        return base
    note = (
        "Urgency was increased by one level because the patient is over 64 (maximum: 5)."
        if changed
        else "The over-64 rule was applied; urgency was already 5, so it did not change."
    )
    return f"{base} {note}".strip()


def _ml_guidance(signals: MLSignals) -> str | None:
    lines = []
    if signals.complaint_category:
        lines.append(f"Complaint category used by the urgency model: {signals.complaint_category}.")
    if signals.esi_level is not None:
        lines.append(
            f"FedMML urgency prediction: project scale {signals.urgency_level}/5 "
            f"(1=not urgent, 5=very urgent); corresponding ESI={signals.esi_level}/5; "
            f"model probability={signals.urgency_confidence:.3f}. Advisory only; verify against the supplied symptoms and vital signs."
        )
    confident_specialties = [
        candidate
        for candidate in (signals.specialties.candidates if signals.specialties else [])
        if candidate.confidence >= 0.30
    ]
    if confident_specialties:
        candidates = ", ".join(
            f"{candidate.specialty} ({candidate.confidence:.3f})"
            for candidate in confident_specialties
        )
        lines.append(
            "Kaggle transcription classifier specialty candidates (noisy and advisory): "
            f"{candidates}."
        )
    return "\n".join(lines) if lines else None


def _seviye(durum: str) -> int:
    durum = str(durum).upper()
    return SEVIYELER.index(durum) if durum in SEVIYELER else 0


def _en_acil(*durumlar: str) -> str:
    return max(durumlar, key=_seviye)


BILINC_SEVIYELERI = ("A", "C", "V", "P", "U")


def _deger(kaynak: Any, anahtar: str, varsayilan: Any) -> Any:
    """Read a field from a Pydantic model, ORM row, or dict."""
    if isinstance(kaynak, dict):
        return kaynak.get(anahtar, varsayilan)
    return getattr(kaynak, anahtar, varsayilan)


def news2_hesapla(vitaller: Any) -> tuple[int, list[str]]:
    """Calculate the Royal College of Physicians NEWS2 score.

    Uses SpO2 scale 1. Consciousness is ACVPU: anything other than A (alert),
    including new confusion, scores 3. Supplemental oxygen adds 2.
    """
    def _v(key, default):
        deger = _deger(vitaller, key, default)
        return default if deger is None else deger

    solunum = int(_v("solunum", 16))
    spo2 = int(_v("spo2", 98))
    sistolik = int(_v("tansiyon_sistolik", 120))
    nabiz = int(_v("nabiz", 80))
    ates = float(_v("ates", 36.8))
    bilinc = str(_v("bilinc", "A") or "A").upper()
    ek_oksijen = bool(_v("ek_oksijen", False))

    puanlar = {
        "Respiratory rate": 3 if solunum <= 8 else 1 if solunum <= 11 else 0 if solunum <= 20 else 2 if solunum <= 24 else 3,
        "SpO2": 3 if spo2 <= 91 else 2 if spo2 <= 93 else 1 if spo2 <= 95 else 0,
        "Systolic blood pressure": 3 if sistolik <= 90 else 2 if sistolik <= 100 else 1 if sistolik <= 110 else 0 if sistolik <= 219 else 3,
        "Heart rate": 3 if nabiz <= 40 else 1 if nabiz <= 50 else 0 if nabiz <= 90 else 1 if nabiz <= 110 else 2 if nabiz <= 130 else 3,
        "Temperature": 3 if ates <= 35.0 else 1 if ates <= 36.0 else 0 if ates <= 38.0 else 1 if ates <= 39.0 else 2,
        "Consciousness": 0 if bilinc == "A" else 3,
        "Supplemental oxygen": 2 if ek_oksijen else 0,
    }

    toplam = sum(puanlar.values())
    kritikler = [param for param, p in puanlar.items() if p == 3]
    return toplam, kritikler


def kural_tabanli_degerlendir(istek: Any) -> tuple[str, str, int]:
    """Run deterministic clinical triage rules without an LLM."""
    vitaller = getattr(istek, "vitaller", istek)
    sikayet = getattr(istek, "sikayet", istek)

    toplam_news, kritikler = news2_hesapla(vitaller)

    ana_sikayet = ""
    agri = 1
    if hasattr(sikayet, "ana_sikayet"):
        ana_sikayet = katla(str(sikayet.ana_sikayet))
        agri = getattr(sikayet, "agri_skalasi", 1)
    elif isinstance(sikayet, dict):
        ana_sikayet = katla(str(sikayet.get("ana_sikayet", "")))
        agri = int(sikayet.get("agri_skalasi", 1))

    # ESI level 1 includes patients who respond only to pain or not at all (P or U on AVPU).
    if str(_deger(vitaller, "bilinc", None) or "A").upper() in ("P", "U"):
        return "KIRMIZI", "The patient responds only to pain or is unresponsive (AVPU).", toplam_news

    if _terim_var(ana_sikayet, _KRITIK_DESEN):
        return "KIRMIZI", "A potentially life-threatening symptom was reported.", toplam_news

    if toplam_news >= 7 or len(kritikler) >= 1:
        return (
            "KIRMIZI",
            f"Critical NEWS2 finding (score {toplam_news}). Critical parameters: {', '.join(kritikler) or 'none'}.",
            toplam_news,
        )

    if toplam_news >= 5:
        return "SARI", f"Moderate vital-sign deterioration (NEWS2: {toplam_news}).", toplam_news

    if agri >= 7:
        return "SARI", f"Severe pain reported ({agri}/10).", toplam_news

    if _terim_var(ana_sikayet, _ACIL_DESEN):
        return "SARI", "A symptom requiring urgent assessment was reported.", toplam_news

    return "YESIL", "Vital signs are stable; no urgent risk was identified.", toplam_news


def _ai_birimleri(ai_cikti: dict) -> tuple[str, list[BirimUyumDetay]]:
    """Validate the LLM's departments against the closed list and clamp the scores."""
    birimler: list[BirimUyumDetay] = []
    for b in ai_cikti.get("birim_uyumluluk_siralamasi") or []:
        if not isinstance(b, dict):
            continue
        bolum = poliklinik_esle(b.get("birim"))
        if not bolum or any(mevcut.birim == bolum for mevcut in birimler):
            continue
        try:
            skor = min(max(float(b.get("uyum_skoru", 0.5)), 0.0), 1.0)
        except (TypeError, ValueError):
            skor = 0.5
        birimler.append(BirimUyumDetay(birim=bolum, uyum_skoru=skor, gerekce=str(b.get("gerekce") or "")))
    birimler.sort(key=lambda b: b.uyum_skoru, reverse=True)

    oneri = poliklinik_esle(ai_cikti.get("onerilen_poliklinik"))
    if oneri is None:
        if ai_cikti.get("onerilen_poliklinik"):
            logger.warning("LLM recommended a department outside the configured list; using a listed one")
        oneri = birimler[0].birim if birimler else ACIL_SERVIS
    return oneri, birimler


def triaj_karari_ver(istek: Any, referanslar: Iterable[Any] | None = None) -> TriajKarari:
    """Combine the rules, ML signals, and LLM response to produce a triage decision.

    ``referanslar`` are disease-to-department reference rows; when given, they are
    added to the LLM prompt as routing guidance. Called by the FastAPI endpoint:
        decision = triaj_karari_ver(istek, referanslar)
    """
    kural_durum, kural_gerekce, news_skor = kural_tabanli_degerlendir(istek)

    try:
        ml_signals = _ml_signals(istek)
    except Exception:
        logger.exception("ML inference failed; continuing with triage rules and the LLM")
        ml_signals = MLSignals()
    referans_baglami = format_referans_baglami(referanslar, ml_signals.english_text or "")
    news2 = news2_hesapla(getattr(istek, "vitaller", istek))
    tam_prompt = build_full_triage_prompt(istek, _ml_guidance(ml_signals), referans_baglami, news2)

    ai_cikti = llm_client.generate(tam_prompt, triaj_sistem_istemi(), json_schema=triaj_json_semasi())
    kaynak = llm_client.provider.upper() if ai_cikti else "KURAL"

    if ai_cikti:
        ai_durum = str(ai_cikti.get("durum", "SARI")).upper()
        if ai_durum not in SEVIYELER:
            ai_durum = "SARI"
        ai_esi = _esi_for_ai_decision(ai_durum, ai_cikti.get("risk_skoru"))
        esi_candidates = [
            _esi_for_status(kural_durum),
            _esi_for_status(ai_durum),
            ai_esi,
        ]
        final_esi = min(esi_candidates)
        final_esi, age_eligible, age_changed = _apply_age_adjustment(final_esi, istek)
        kesin_durum = _status_for_esi(final_esi)

        onerilen_poliklinik, birimler = _ai_birimleri(ai_cikti)

        return TriajKarari(
            durum=kesin_durum,
            risk_skoru=final_esi,
            onerilen_poliklinik=onerilen_poliklinik,
            birim_uyumluluk_siralamasi=birimler,
            kritik_bulgu=str(ai_cikti.get("kritik_bulgu") or kural_gerekce),
            erken_uyari_notu=str(
                ai_cikti.get("erken_uyari_notu") or "Continue to monitor the patient's vital signs closely."
            ),
            aciklama=_age_adjustment_note(
                ai_cikti.get("aciklama") or kural_gerekce, age_eligible, age_changed
            ),
            karar_kaynagi="+".join(
                source for source, enabled in (
                    (kaynak, kaynak != "KURAL"),
                    ("ML", ml_signals.esi_level is not None or bool(ml_signals.specialties)),
                    ("KURAL", True),
                    ("AGE_64_PLUS", age_eligible),
                ) if enabled
            ),
            news2_skoru=news_skor,
        )

    final_esi = _esi_for_status(kural_durum)
    final_esi, age_eligible, age_changed = _apply_age_adjustment(final_esi, istek)
    final_status = _status_for_esi(final_esi)
    candidates = ml_signals.specialties.candidates if ml_signals.specialties else []
    specialty_candidates = [candidate for candidate in candidates if candidate.confidence >= 0.30]
    complaint = katla(str(getattr(getattr(istek, "sikayet", istek), "ana_sikayet", "")))
    # Resuscitation-level patients stay in the emergency department. Otherwise the
    # keyword router (which understands Turkish and negation) comes first, then the
    # ML specialty model, then Emergency Medicine.
    kural_bolumu = None if final_status == "KIRMIZI" else sikayetten_poliklinik(complaint)
    if final_status == "KIRMIZI":
        varsayilan_poliklinik = ACIL_SERVIS
    elif kural_bolumu:
        varsayilan_poliklinik = kural_bolumu
    elif specialty_candidates:
        varsayilan_poliklinik = specialty_candidates[0].specialty
    else:
        varsayilan_poliklinik = ACIL_SERVIS

    birimler = [
        BirimUyumDetay(
            birim=varsayilan_poliklinik,
            uyum_skoru=1.0 if kural_bolumu or final_status == "KIRMIZI" else 0.5,
            gerekce="Matched the reported symptoms." if kural_bolumu else kural_gerekce,
        )
    ]
    birimler += [
        BirimUyumDetay(
            birim=candidate.specialty,
            uyum_skoru=candidate.confidence,
            gerekce="Candidate suggested by the clinical transcription specialty model.",
        )
        for candidate in specialty_candidates
        if candidate.specialty != varsayilan_poliklinik
    ]

    return TriajKarari(
        durum=final_status,
        risk_skoru=final_esi,
        onerilen_poliklinik=varsayilan_poliklinik,
        birim_uyumluluk_siralamasi=birimler,
        kritik_bulgu=kural_gerekce,
        erken_uyari_notu="Model-based triage was unavailable; a nurse or physician must review this result.",
        aciklama=_age_adjustment_note(kural_gerekce, age_eligible, age_changed),
        karar_kaynagi="+".join(
            source for source, enabled in (
                ("ML", bool(specialty_candidates) and not kural_bolumu and final_status != "KIRMIZI"),
                ("KURAL", True),
                ("AGE_64_PLUS", age_eligible),
            ) if enabled
        ),
        news2_skoru=news_skor,
    )
