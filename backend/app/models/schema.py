"""Shared input schema for the triage prototype.

All measurements are optional because the source dataset contains missing
vitals and selectively ordered laboratory tests.
"""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PatientIntake:
    chief_complaint: str
    age: float | None = None
    sex: str | None = None
    clinical_notes: str | None = None
    systolic_bp: float | None = None
    diastolic_bp: float | None = None
    heart_rate: float | None = None
    respiratory_rate: float | None = None
    temperature: float | None = None
    spo2: float | None = None
    pain_score: float | None = None
    wbc: float | None = None
    hemoglobin: float | None = None
    platelet_count: float | None = None
    sodium: float | None = None
    potassium: float | None = None
    creatinine: float | None = None
    glucose: float | None = None
    troponin: float | None = None
    bnp: float | None = None
    lactate: float | None = None
    inr: float | None = None

    @classmethod
    def from_mapping(cls, values: dict[str, Any]) -> "PatientIntake":
        allowed = cls.__dataclass_fields__.keys()
        clean = {key: value for key, value in values.items() if key in allowed}
        clean.setdefault("chief_complaint", "")
        return cls(**clean)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
