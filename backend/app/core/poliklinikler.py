"""Closed list of departments the triage may recommend, and name normalization.

Every recommended department (from the LLM, the ML specialty model, or the
rules) is mapped onto this list, so the queue and history always show the same
spelling. Override the list with the POLIKLINIKLER setting (comma-separated).
"""

import difflib
import re
from functools import lru_cache

from app.core.config import settings

ACIL_SERVIS = "Emergency Medicine"

VARSAYILAN_POLIKLINIKLER = (
    ACIL_SERVIS,
    "Internal Medicine",
    "Cardiology",
    "Pulmonology",
    "Neurology",
    "Neurosurgery",
    "General Surgery",
    "Thoracic Surgery",
    "Cardiovascular Surgery",
    "Orthopedics and Traumatology",
    "Urology",
    "Nephrology",
    "Gastroenterology",
    "Endocrinology",
    "Infectious Diseases",
    "Hematology",
    "Rheumatology",
    "Obstetrics and Gynecology",
    "Pediatrics",
    "Otolaryngology",
    "Ophthalmology",
    "Dermatology",
    "Psychiatry",
    "Plastic Surgery",
    "Physical Medicine and Rehabilitation",
    "Interventional Radiology",
    "Dentistry",
)

# Common alternative names, including the MTSamples specialty labels used by the
# ML model. Labels that are not clinics (for example Radiology or Letters) are absent
# on purpose, so they are dropped instead of being recommended.
_ESANLAMLILAR = {
    "emergency": ACIL_SERVIS,
    "emergency department": ACIL_SERVIS,
    "emergency room": ACIL_SERVIS,
    "er": ACIL_SERVIS,
    "ed": ACIL_SERVIS,
    "acil": ACIL_SERVIS,
    "acil servis": ACIL_SERVIS,
    "general medicine": "Internal Medicine",
    "dahiliye": "Internal Medicine",
    "ic hastaliklari": "Internal Medicine",
    "cardiovascular pulmonary": "Cardiology",
    "kardiyoloji": "Cardiology",
    "pulmonary medicine": "Pulmonology",
    "respiratory medicine": "Pulmonology",
    "chest diseases": "Pulmonology",
    "gogus hastaliklari": "Pulmonology",
    "noroloji": "Neurology",
    "surgery": "General Surgery",
    "genel cerrahi": "General Surgery",
    "bariatrics": "General Surgery",
    "cardiothoracic surgery": "Thoracic Surgery",
    "orthopedic": "Orthopedics and Traumatology",
    "orthopedics": "Orthopedics and Traumatology",
    "orthopaedics": "Orthopedics and Traumatology",
    "orthopedic surgery": "Orthopedics and Traumatology",
    "traumatology": "Orthopedics and Traumatology",
    "ortopedi": "Orthopedics and Traumatology",
    "infectious disease": "Infectious Diseases",
    "hematology oncology": "Hematology",
    "obstetrics gynecology": "Obstetrics and Gynecology",
    "obstetrics": "Obstetrics and Gynecology",
    "gynecology": "Obstetrics and Gynecology",
    "kadin dogum": "Obstetrics and Gynecology",
    "pediatrics neonatal": "Pediatrics",
    "pediatric": "Pediatrics",
    "ent": "Otolaryngology",
    "ent otolaryngology": "Otolaryngology",
    "ear nose and throat": "Otolaryngology",
    "otorhinolaryngology": "Otolaryngology",
    "kbb": "Otolaryngology",
    "psychiatry psychology": "Psychiatry",
    "cosmetic plastic surgery": "Plastic Surgery",
    "physical medicine rehab": "Physical Medicine and Rehabilitation",
    "physical medicine": "Physical Medicine and Rehabilitation",
}

_TURKCE_ASCII = str.maketrans("çğıİöşüÇĞÖŞÜ", "cgiIosuCGOSU")


def _anahtar(ad: str) -> str:
    metin = str(ad).translate(_TURKCE_ASCII).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", metin).split())


@lru_cache(maxsize=1)
def poliklinik_listesi() -> tuple[str, ...]:
    """Return the configured departments; Emergency Medicine is always included."""
    ozel = [ad.strip() for ad in (settings.POLIKLINIKLER or "").split(",") if ad.strip()]
    liste = ozel or list(VARSAYILAN_POLIKLINIKLER)
    if ACIL_SERVIS not in liste:
        liste.insert(0, ACIL_SERVIS)
    return tuple(dict.fromkeys(liste))


@lru_cache(maxsize=1)
def _dizin() -> dict[str, str]:
    liste = poliklinik_listesi()
    dizin = {_anahtar(ad): ad for ad in liste}
    for esanlamli, hedef in _ESANLAMLILAR.items():
        if hedef in liste:
            dizin.setdefault(_anahtar(esanlamli), hedef)
    return dizin


@lru_cache(maxsize=1024)
def poliklinik_esle(ad: object) -> str | None:
    """Map a department name onto the closed list; return None when nothing fits."""
    if not isinstance(ad, str) or not ad.strip():
        return None
    anahtar = _anahtar(ad)
    dizin = _dizin()
    if anahtar in dizin:
        return dizin[anahtar]
    yakin = difflib.get_close_matches(anahtar, list(dizin), n=1, cutoff=0.88)
    return dizin[yakin[0]] if yakin else None


# --- Rule-based routing (used when no LLM decision is available) ----------------

# (department, Turkish word-start keywords, English whole-word keywords[, weight]).
# Text is folded with katla first. Turkish nouns change their stem with suffixes
# ("karin" becomes "karnim", "burun" becomes "burnum"), so both forms are listed.
# Order breaks ties: more specific departments come first.
_YONLENDIRME_KURALLARI = (
    ("Obstetrics and Gynecology",
     ("hamile", "gebe", "adet gecik", "adetim gecik", "adet kanama", "vajinal", "rahim", "dogum sanc",
      "su geldi", "regl"),
     ("pregnant", "pregnancy", "vaginal", "missed period", "menstrual", "pelvic pain")),
    ("Ophthalmology",
     ("goz", "gorme", "bulanik gor", "cift gor"),
     ("eye", "vision", "blurred vision", "double vision")),
    ("Otolaryngology",
     ("bogaz", "kulak", "burun", "burnu", "bademcik", "sinuzit", "isitme", "cinlama", "yutkun", "hapsir"),
     ("throat", "ear", "earache", "nose", "nosebleed", "sinus", "tonsil", "hearing", "tinnitus")),
    ("Dentistry",
     ("dis agri", "disim", "dis eti", "dislerim", "agiz ici"),
     ("tooth", "toothache", "gum", "dental")),
    ("Psychiatry",
     ("intihar", "kendime zarar", "kendini oldur", "panik atak", "depresyon", "anksiyete", "halusinasyon",
      "sesler duyuyor"),
     ("suicidal", "suicide", "self harm", "panic attack", "depression", "anxiety", "hallucination")),
    ("Nephrology",
     ("diyaliz", "bobrek yetmez", "bobrek hastal"),
     ("dialysis", "kidney disease", "kidney failure")),
    ("Urology",
     ("idrar", "bobrek tasi", "bobrek agri", "yan agri", "bogrum", "prostat", "testis", "tas dusur"),
     ("urination", "urinating", "urinate", "urine", "urinary", "flank pain", "kidney stone", "prostate",
      "testicular")),
    ("Orthopedics and Traumatology",
     ("kirik", "kirild", "burkul", "cikik", "dustum", "dustu", "bilek", "diz agri", "dizim", "omuz",
      "bel agri", "belim", "sirt agri", "kalca", "ayak bileg", "incinme", "travma"),
     ("fracture", "sprain", "dislocation", "fell", "fall", "wrist", "ankle", "knee", "shoulder",
      "back pain", "hip", "injury")),
    ("Neurology",
     ("bas agri", "basim agri", "migren", "bas donme", "basim don", "uyusma", "uyusuyor", "felc", "inme",
      "konusma bozuk", "pelteklest", "yuz kaym", "agzi kay", "nobet", "havale", "titreme nobet", "gucsuz"),
     ("headache", "migraine", "dizziness", "numbness", "stroke", "seizure", "slurred speech", "weakness")),
    ("Cardiology",
     ("gogus agri", "gogsumde agri", "gogus bask", "gogsumde bask", "gogsum sikis", "gogus sikis", "carpinti",
      "kalp", "ritim"),
     ("chest pain", "chest pressure", "chest tightness", "palpitation", "palpitations", "heart")),
    ("Pulmonology",
     ("nefes darlig", "nefes alam", "oksuruk", "oksuru", "balgam", "hiriltili", "astim", "koah", "kan tukur"),
     ("shortness of breath", "cough", "coughing", "sputum", "wheezing", "asthma", "copd")),
    ("General Surgery",
     ("sag alt karin", "sag alt karn", "karnimin sag alt", "fitik", "apandisit", "safra", "sag ust karin",
      "sag ust karn", "karnimin sag ust", "kasikta sislik", "yagli yemek", "makatta"),
     ("appendicitis", "hernia", "gallbladder", "right lower abdominal", "right lower quadrant",
      "right upper abdominal", "fatty meal", "fatty meals", "groin bulge", "bulge"),
     2),
    ("Gastroenterology",
     ("ishal", "kabiz", "mide", "hazimsiz", "reflu", "kanli diski", "siyah diski", "kan kus", "karin agri",
      "karnim agri", "karin kramp", "bulanti", "kusma", "kusuyor"),
     ("diarrhea", "constipation", "stomach", "heartburn", "reflux", "black stool", "vomiting blood",
      "abdominal pain", "nausea", "vomiting")),
    ("Dermatology",
     ("dokuntu", "kasinti", "kasiniyor", "sivilce", "egzama", "cilt", "deri", "kurdesen"),
     ("rash", "itching", "itchy", "acne", "eczema", "skin", "hives")),
    ("Endocrinology",
     ("sekerim yuksek", "seker yuksek", "kan sekeri", "tiroid", "guatr"),
     ("blood sugar", "thyroid", "diabetes")),
    ("Hematology",
     ("morarma", "kansizlik", "anemi", "kan degerleri dusuk"),
     ("bruising", "anemia", "low blood count", "low blood counts")),
    ("Rheumatology",
     ("eklem agri", "eklemlerim", "sabah tutuklu"),
     ("joint pain", "joint swelling", "morning stiffness")),
    ("Infectious Diseases",
     ("titreme", "yurt disi donus"),
     ("chills", "after travel")),
    ("Internal Medicine",
     ("halsiz", "yorgun", "tansiyon", "kilo kayb", "ates"),
     ("fatigue", "tired", "blood pressure", "weight loss", "fever")),
)


@lru_cache(maxsize=1)
def _yonlendirme_desenleri():
    from app.core.anahtar_kelime import desen

    liste = set(poliklinik_listesi())
    return tuple(
        (kural[0], desen(kural[1], kural[2]), kural[3] if len(kural) > 3 else 1)
        for kural in _YONLENDIRME_KURALLARI
        if kural[0] in liste
    )


def sikayetten_poliklinik(katlanmis_metin: str) -> str | None:
    """Pick the department whose keywords best match a folded complaint text.

    Negated symptoms do not count. Returns None when nothing matches, so the
    caller can fall back to another signal or to Emergency Medicine.
    """
    from app.core.anahtar_kelime import eslesme_sayisi

    en_iyi, en_iyi_puan = None, 0
    for bolum, desen_, agirlik in _yonlendirme_desenleri():
        puan = eslesme_sayisi(katlanmis_metin, desen_) * agirlik
        if puan > en_iyi_puan:
            en_iyi, en_iyi_puan = bolum, puan
    return en_iyi
