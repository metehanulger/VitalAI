import json
import os
from dataclasses import dataclass
from typing import Any, Protocol

from dotenv import load_dotenv

from .schema import PatientIntake

load_dotenv()


SYSTEM_PROMPT = """You are a careful emergency-department intake assistant speaking Turkish.
Collect a concise chief complaint and clarify relevant symptoms. Use only facts
the patient or nurse supplied; never invent measurements, diagnoses, or history.
Do not assign an ESI level or choose a hospital department. Measurements are
optional. Ask only a few useful follow-up questions when information is missing.
If the described symptoms suggest immediate danger, clearly tell the user to
alert the nurse or call local emergency services now. Return only JSON with:
normalized_complaint (string), follow_up_questions (array of strings),
red_flags (array of strings explicitly reported), and patient_message (string).
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


class GeminiChatClient:
    """Google Gemini adapter; reads credentials from GEMINI_API_KEY."""

    def __init__(self, model: str | None = None):
        try:
            from google import genai
        except ImportError as error:
            raise RuntimeError("Install the 'google-genai' dependency to use the Gemini intake.") from error
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Set GEMINI_API_KEY in the environment or project .env file.")
        self.client = genai.Client(api_key=api_key)
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    def complete(self, *, system: str, user: str) -> str:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=user,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        content = response.text
        if not content:
            raise ValueError("Gemini returned an empty response.")
        return content


class TriageIntakeAssistant:
    def __init__(self, client: ChatClient):
        self.client = client

    def collect(self, complaint: str, measurements: dict[str, Any] | None = None) -> IntakeConversation:
        measurements = measurements or {}
        intake = PatientIntake.from_mapping({**measurements, "chief_complaint": complaint})
        user_message = json.dumps(
            {"chief_complaint": complaint, "provided_measurements": measurements},
            ensure_ascii=False,
        )
        raw = self.client.complete(system=SYSTEM_PROMPT, user=user_message)
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError("LLM response was not valid JSON.") from error
        normalized = str(result.get("normalized_complaint") or complaint).strip()
        intake.chief_complaint = normalized
        return IntakeConversation(
            structured_intake=intake,
            normalized_complaint=normalized,
            follow_up_questions=[str(value) for value in result.get("follow_up_questions", [])],
            red_flags=[str(value) for value in result.get("red_flags", [])],
            patient_message=str(result.get("patient_message", "")),
        )
