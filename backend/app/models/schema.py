"""Patient model input matching the four triage cards.

Personal identifiers and hospital-log fields are retained only for application
storage. ``to_model_dict`` deliberately excludes them from ML and Gemini input.
"""

from dataclasses import asdict, dataclass
import unicodedata
from typing import Any, Mapping


def normalize_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("ı", "i")
    return " ".join(text.replace("_", " ").replace("-", " ").split())


NUMERIC_FIELDS = {
    "age", "height_cm", "weight_kg", "pulse", "systolic_bp", "diastolic_bp",
    "respiratory_rate", "temperature_c", "spo2", "pain_score",
}

MODEL_FIELDS = (
    "age", "height_cm", "weight_kg", "blood_type", "chronic_conditions",
    "regular_medications", "pulse", "systolic_bp", "diastolic_bp",
    "respiratory_rate", "temperature_c", "spo2", "chief_complaint", "pain_score",
)

FIELD_ALIASES = {
    "full_name": {"full name", "name", "isim", "ad soyad", "hasta adi"},
    "age": {"age", "yas"},
    "height_cm": {"height", "height cm", "boy", "boy cm"},
    "weight_kg": {"weight", "weight kg", "kilo", "agirlik"},
    "blood_type": {"blood type", "blood group", "kan grubu"},
    "identity_type": {"identity type", "kimlik turu", "kimlik tipi"},
    "identity_number": {
        "identity number", "identity no", "kimlik no", "tc kimlik no",
        "passport no", "pasaport no",
    },
    "chronic_conditions": {
        "chronic conditions", "chronic condition", "kronik rahatsizlik",
        "kronik hastalik",
    },
    "regular_medications": {
        "regular medications", "medications", "surekli ilac", "duzenli ilac",
    },
    "pulse": {"pulse", "nabiz", "heart rate", "heart_rate"},
    "systolic_bp": {"systolic bp", "systolic", "sistolik", "sistolik tansiyon", "tansiyon sistolik"},
    "diastolic_bp": {"diastolic bp", "diastolic", "diastolik", "diastolik tansiyon", "tansiyon diyastolik", "tansiyon diastolik"},
    "respiratory_rate": {"respiratory rate", "respiratory_rate", "solunum", "solunum sayisi"},
    "temperature_c": {"temperature", "temperature c", "temperature_c", "ates", "vucut sicakligi"},
    "spo2": {"spo2", "sp o2", "oxygen saturation", "oksijen saturasyonu"},
    "chief_complaint": {"chief complaint", "chief_complaint", "ana sikayet", "sikayet"},
    "pain_score": {"pain score", "pain_score", "agri skalasi", "agri puani"},
    "patient_status": {"patient status", "patient_status", "hasta durumu", "durum"},
}

ALIAS_TO_FIELD = {
    normalize_key(alias): field
    for field, aliases in FIELD_ALIASES.items()
    for alias in aliases | {field}
}


def _flatten_cards(values: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in values.items():
        if normalize_key(key) in {"hastane log", "hospital log"}:
            continue
        if isinstance(value, Mapping):
            flattened.update(_flatten_cards(value))
        else:
            field = ALIAS_TO_FIELD.get(normalize_key(key))
            if field:
                flattened[field] = value
    return flattened


def _optional_float(value: Any, field: str) -> float | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"'{field}' must be numeric or empty; received {value!r}.") from error


@dataclass
class PatientIntake:
    chief_complaint: str | None = None
    age: float | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    blood_type: str | None = None
    identity_type: str | None = None
    identity_number: str | None = None
    full_name: str | None = None
    chronic_conditions: str | None = None
    regular_medications: str | None = None
    pulse: float | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    respiratory_rate: float | None = None
    temperature_c: float | None = None
    spo2: float | None = None
    pain_score: float | None = None
    patient_status: str | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "PatientIntake":
        clean = _flatten_cards(values)
        for field in NUMERIC_FIELDS:
            clean[field] = _optional_float(clean.get(field), field)
        return cls(**{key: value for key, value in clean.items() if key in cls.__dataclass_fields__})

    def to_dict(self) -> dict[str, Any]:
        """Return all intake fields for controlled application storage."""
        return asdict(self)

    def to_model_dict(self) -> dict[str, Any]:
        """Return only clinical model features; never include name or ID."""
        values = asdict(self)
        return {field: values[field] for field in MODEL_FIELDS}
