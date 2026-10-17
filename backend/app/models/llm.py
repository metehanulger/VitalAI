from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field

class BirimUyumluluk(BaseModel):
    """A candidate clinic and its model-generated compatibility score."""
    birim: str = Field(..., description="Hospital clinic or specialty name")
    uyum_skoru: float = Field(..., ge=0.0, le=1.0, description="Compatibility score from 0.0 to 1.0")
    gerekce: str = Field(..., description="Clinical rationale for the suggested clinic")


class LLMTriageOutput(BaseModel):
    """Structured triage output stored in the hospital log."""
    Risk_Skoru: int = Field(..., ge=1, le=5, description="ESI level: 1 is most urgent and 5 is least urgent")
    Renk_Kodu: Literal["RED", "YELLOW", "GREEN"] = Field(..., description="Triage area color")
    Onerilen_Poliklinik: str = Field(..., description="Primary recommended medical specialty")
    Birim_Uyumluluk_Siralamasi: List[BirimUyumluluk] = Field(
        default_factory=list,
        description="Clinic recommendations sorted from highest to lowest compatibility"
    )
    Kritik_Bulgu: str = Field(..., description="Summary of the key finding(s) affecting the decision")
    Erken_Uyari_Notu: str = Field(..., description="Brief early-warning note for clinical staff")


class HastaneLogResponse(LLMTriageOutput):
    """API response containing the triage result and linked intake record IDs."""
    log_id: str = Field(..., description="Hospital master log ID")
    demografi_id: str = Field(..., description="Demographics card record ID")
    tibbi_gecmis_id: str = Field(..., description="Medical history card record ID")
    vitaller_id: str = Field(..., description="Vitals card record ID")
    sikayet_id: str = Field(..., description="Complaint card record ID")

    tarih_saat: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    ai_provider: str = Field(default="Google-Gemini")

import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from dotenv import load_dotenv

from .ml import TriagePrediction
from .schema import PatientIntake

load_dotenv()


INTAKE_SYSTEM_PROMPT = """You are a patient intake assistant supporting an emergency department nurse.
Use only the clinical information provided. Do not invent measurements, diagnoses,
or medical history. Do not ask for identity information. Do not assign an ESI/urgency
level or select a clinic. Identify missing information and ask brief follow-up
questions. If an immediate life-threatening condition is explicitly described, tell
the patient to alert a nurse at once. Respond in English and return only JSON with:
normalized_complaint (string), follow_up_questions (string array),
red_flags (string array), and patient_message (string).
"""

RECOMMENDATION_SYSTEM_PROMPT = """You are an emergency department nurse decision-support assistant.
Patient information and an urgency level assigned by the ML model will be provided.
Never change the urgency level; report the ML level exactly as given. Based on the
complaint and clinical information, recommend an appropriate clinic and provide a
brief, clear rationale. Do not diagnose or invent information. Patient names,
identity numbers, and hospital-log fields are not provided. State that a nurse or
physician must verify the recommendation. Respond in English and return only JSON
with: clinic (string), rationale (string), patient_message (string), and
red_flags (string array).
"""


class ChatClient(Protocol):
    def complete(self, *, system: str, user: str) -> str: ...


@dataclass
class IntakeConversation:
    structured_intake: PatientIntake
    normalized_complaint: str
    follow_up_questions: list[str]
    red_flags: list[str]
    patient_message: str


@dataclass
class TriageRecommendation:
    clinic: str
    urgency_level: int
    urgency_label: str
    rationale: str
    red_flags: list[str]
    patient_message: str

    def to_text(self) -> str:
        flags = f"\nRed flags: {', '.join(self.red_flags)}" if self.red_flags else ""
        return (
            f"Recommended clinic: {self.clinic}\n"
            f"Urgency: {self.urgency_level}/5 — {self.urgency_label}\n"
            f"Rationale: {self.rationale}{flags}\n"
            f"Information: {self.patient_message}"
        )


class GeminiChatClient:
    """Google Gemini adapter; reads credentials from GEMINI_API_KEY."""

    def __init__(self, model: str | None = None):
        try:
            import google.generativeai as genai
        except ImportError as error:
            raise RuntimeError("Install the 'google-generativeai' dependency to use Gemini.") from error
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY in the environment or project .env file.")
        genai.configure(api_key=api_key)
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.client = genai.GenerativeModel(self.model)

    def complete(self, *, system: str, user: str) -> str:
        response = self.client.generate_content(
            f"{system}\n\nReturn a valid JSON object only.\n\n{user}",
            generation_config={"response_mime_type": "application/json", "temperature": 0.2},
        )
        content = getattr(response, "text", None)
        if not content:
            raise ValueError("Gemini returned an empty response.")
        return content


class TriageIntakeAssistant:
    def __init__(self, client: ChatClient):
        self.client = client

    def collect(
        self,
        complaint: str | None = None,
        measurements: dict[str, Any] | None = None,
    ) -> IntakeConversation:
        intake = PatientIntake.from_mapping(measurements or {})
        if complaint and complaint.strip():
            intake.chief_complaint = complaint.strip()
        user_message = json.dumps(intake.to_model_dict(), ensure_ascii=False)
        result = self._parse_json(self.client.complete(system=INTAKE_SYSTEM_PROMPT, user=user_message))
        normalized = str(result.get("normalized_complaint") or intake.chief_complaint or "").strip()
        intake.chief_complaint = normalized
        return IntakeConversation(
            structured_intake=intake,
            normalized_complaint=normalized,
            follow_up_questions=[str(value) for value in result.get("follow_up_questions", [])],
            red_flags=[str(value) for value in result.get("red_flags", [])],
            patient_message=str(result.get("patient_message", "")),
        )

    def recommend(
        self,
        intake: PatientIntake | dict[str, Any],
        prediction: TriagePrediction,
    ) -> TriageRecommendation:
        patient = intake if isinstance(intake, PatientIntake) else PatientIntake.from_mapping(intake)
        user_message = json.dumps(
            {
                "patient_data": patient.to_model_dict(),
                "ml_urgency_level": prediction.urgency_level,
                "ml_urgency_label": prediction.urgency_label,
                "ml_confidence": prediction.confidence,
            },
            ensure_ascii=False,
        )
        result = self._parse_json(
            self.client.complete(system=RECOMMENDATION_SYSTEM_PROMPT, user=user_message)
        )
        return TriageRecommendation(
            clinic=str(result.get("clinic") or "Emergency department evaluation required").strip(),
            urgency_level=prediction.urgency_level,
            urgency_label=prediction.urgency_label,
            rationale=str(result.get("rationale", "")),
            red_flags=[str(value) for value in result.get("red_flags", [])],
            patient_message=str(
                result.get("patient_message")
                or "A nurse or physician must verify this recommendation."
            ),
        )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError("Gemini response was not valid JSON.") from error
        if not isinstance(value, dict):
            raise ValueError("Gemini response must be a JSON object.")
        return value
