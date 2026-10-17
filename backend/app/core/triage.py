"""Emergency department pre-triage decision engine (LLM + NEWS2 / clinical rules).

This module:
1. Processes the four intake cards using the master prompt and configured LLM.
2. Calculates the NEWS2 clinical deterioration score from vital signs.
3. Combines rule-based and AI results; the AI cannot lower rule-based urgency.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional, List, Any

from app.core.prompts import build_full_triage_prompt, MASTER_TRIAGE_PROMPT
from app.core.llm_client import llm_client
from app.core.config import settings
from app.core.metin import katla
from app.models.ml import ClinicalSpecialtyClassifier, SpecialtyPrediction, UrgencyClassifier
from app.models.schema import PatientIntake

logger = logging.getLogger(__name__)

SEVIYELER = ("YESIL", "SARI", "KIRMIZI")

KRITIK_KELIMELER = [
    "bilinc kaybi", "bilinci kapali", "bayildi ve uyanmiyor", "nefes alamiyor", "nefes alamiyorum",
    "solunum durmasi", "kalp durmasi", "felc", "inme",
    "konusamiyor", "nobet", "havale", "siddetli kanama", "intihar", "zehirlen", "anafilaksi",
    "loss of consciousness", "unconscious", "not breathing", "respiratory arrest", "cardiac arrest",
    "stroke", "unable to speak", "seizure", "severe bleeding", "anaphylaxis",
]

ACIL_KELIMELER = [
    "nefes darligi", "kanama", "kirik", "bayil", "carpinti", "kusma", "karin agrisi",
    "yuksek ates", "hamile", "gebe", "yanik", "kafa travmasi", "basini carpti",
    "shortness of breath", "bleeding", "fracture", "fainting", "palpitations", "palpitation",
    "vomiting", "abdominal pain", "high fever", "burn", "head injury", "gogus agrisi",
    "gogsumde agri", "chest pain", "chest pressure", "chest tightness",
]

KARDIYOLOJI_KELIMELERI = (
    "gogus", "carpinti", "chest", "palpitations", "palpitation", "irregular heartbeat",
    "heart rhythm", "racing heart",
)


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


@lru_cache(maxsize=1)
def _load_ml_models():
    """Load trained local model artifacts once per application process."""
    backend_dir = Path(__file__).resolve().parents[2]
    artifact_dir = backend_dir / "model_artifacts"

    def _artifact_path(configured: str | None, filename: str) -> Path:
        path = Path(configured) if configured else artifact_dir / filename
        return path if path.is_absolute() else backend_dir / path

    urgency_path = _artifact_path(
        settings.TRIAGE_URGENCY_MODEL or os.getenv("TRIAGE_URGENCY_MODEL"), "urgency.joblib"
    )
    specialty_path = _artifact_path(
        settings.TRIAGE_SPECIALTY_MODEL or os.getenv("TRIAGE_SPECIALTY_MODEL"), "specialty.joblib"
    )

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
    return urgency_model, specialty_model


def _ml_signals(istek: Any) -> MLSignals:
    urgency_model, specialty_model = _load_ml_models()
    if urgency_model is None and specialty_model is None:
        return MLSignals()

    values = istek.model_dump() if hasattr(istek, "model_dump") else istek
    intake = PatientIntake.from_mapping(values)
    signals = MLSignals()

    if urgency_model is not None:
        prediction = urgency_model.predict(intake)
        signals.urgency_level = prediction.urgency_level
        signals.urgency_confidence = prediction.confidence
        signals.esi_level = 6 - prediction.urgency_level

    if specialty_model is not None:
        complaint = " ".join(
            part for part in (
                intake.chief_complaint or "",
                intake.chronic_conditions or "",
                intake.regular_medications or "",
            ) if part
        )
        classifier_text = complaint
        if complaint:
            translation = llm_client.generate(
                json.dumps({"clinical_text": complaint}, ensure_ascii=False),
                "Translate the supplied patient complaint and brief medical history into concise English. "
                "Preserve only facts explicitly provided; do not diagnose, infer, or add information. "
                'Return only JSON: {"english_text": "..."}.',
            )
            if translation and translation.get("english_text"):
                classifier_text = str(translation["english_text"])
        signals.specialties = specialty_model.predict(classifier_text)
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


def news2_hesapla(vitaller: Any) -> tuple[int, list[str]]:
    """Calculate the Royal College of Physicians NEWS2 score."""
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
        "Respiratory rate": 3 if solunum <= 8 else 1 if solunum <= 11 else 0 if solunum <= 20 else 2 if solunum <= 24 else 3,
        "SpO2": 3 if spo2 <= 91 else 2 if spo2 <= 93 else 1 if spo2 <= 95 else 0,
        "Systolic blood pressure": 3 if sistolik <= 90 else 2 if sistolik <= 100 else 1 if sistolik <= 110 else 0 if sistolik <= 219 else 3,
        "Heart rate": 3 if nabiz <= 40 else 1 if nabiz <= 50 else 0 if nabiz <= 90 else 1 if nabiz <= 110 else 2 if nabiz <= 130 else 3,
        "Temperature": 3 if ates <= 35.0 else 1 if ates <= 36.0 else 0 if ates <= 38.0 else 1 if ates <= 39.0 else 2,
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

    for kelime in KRITIK_KELIMELER:
        if re.search(r"\b" + re.escape(kelime), ana_sikayet):
            return "KIRMIZI", "A potentially life-threatening symptom was reported.", toplam_news

    if toplam_news >= 7 or len(kritikler) >= 1:
        return "KIRMIZI", f"NEWS2 skoru kritik ({toplam_news}). Kritik parametreler: {', '.join(kritikler)}", toplam_news

    if toplam_news >= 5:
        return "SARI", f"Moderate vital-sign deterioration (NEWS2: {toplam_news}).", toplam_news

    if agri >= 7:
        return "SARI", f"Severe pain reported ({agri}/10).", toplam_news

    for kelime in ACIL_KELIMELER:
        if re.search(r"\b" + re.escape(kelime), ana_sikayet):
            return "SARI", "A symptom requiring urgent assessment was reported.", toplam_news

    return "YESIL", "Vital signs are stable; no urgent risk was identified.", toplam_news


def triaj_karari_ver(istek: Any) -> TriajKarari:
    """Combine the master prompt and LLM response to produce a triage decision.

    Called directly by the FastAPI endpoint in api/triage.py:
        decision = triaj_karari_ver(istek)
    """
    kural_durum, kural_gerekce, news_skor = kural_tabanli_degerlendir(istek)

    try:
        ml_signals = _ml_signals(istek)
    except Exception:
        logger.exception("ML inference failed; continuing with triage rules and the LLM")
        ml_signals = MLSignals()
    tam_prompt = build_full_triage_prompt(istek, _ml_guidance(ml_signals))

    ai_cikti = llm_client.generate(tam_prompt, MASTER_TRIAGE_PROMPT)
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

        birimler_raw = ai_cikti.get("birim_uyumluluk_siralamasi", [])
        birimler = []
        for b in birimler_raw:
            birimler.append(BirimUyumDetay(
                birim=b.get("birim", "Emergency Medicine"),
                uyum_skoru=float(b.get("uyum_skoru", 0.5)),
                gerekce=b.get("gerekce", "")
            ))

        return TriajKarari(
            durum=kesin_durum,
            risk_skoru=final_esi,
            onerilen_poliklinik=ai_cikti.get("onerilen_poliklinik", "Emergency Medicine"),
            birim_uyumluluk_siralamasi=birimler,
            kritik_bulgu=ai_cikti.get("kritik_bulgu", kural_gerekce),
            erken_uyari_notu=ai_cikti.get("erken_uyari_notu", "Continue to monitor the patient's vital signs closely."),
            aciklama=_age_adjustment_note(
                ai_cikti.get("aciklama", kural_gerekce), age_eligible, age_changed
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
    critical_complaint = any(
        re.search(r"\b" + re.escape(term), complaint) for term in KRITIK_KELIMELER
    )
    cardiac_complaint = any(
        re.search(r"\b" + re.escape(term), complaint) for term in KARDIYOLOJI_KELIMELERI
    )
    varsayilan_poliklinik = (
        specialty_candidates[0].specialty
        if specialty_candidates
        else ("Cardiology" if cardiac_complaint and not critical_complaint else "Emergency Medicine")
    )
    birimler = [
        BirimUyumDetay(
            birim=candidate.specialty,
            uyum_skoru=candidate.confidence,
            gerekce="Candidate suggested by the clinical transcription specialty model.",
        )
        for candidate in specialty_candidates
    ] or [
        BirimUyumDetay(birim=varsayilan_poliklinik, uyum_skoru=0.5, gerekce=kural_gerekce)
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
                ("ML", bool(specialty_candidates)),
                ("KURAL", True),
                ("AGE_64_PLUS", age_eligible),
            ) if enabled
        ),
        news2_skoru=news_skor,
    )
