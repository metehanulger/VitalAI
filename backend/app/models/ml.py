"""Five-level urgency classifier for the four triage input cards.

The project's scale is 1 (not urgent) through 5 (very urgent). The FedMML
dataset's ESI scale runs in the opposite direction, so ESI labels are inverted
when used as training targets. Hospital color status is never used as a feature.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder
from sklearn.utils.validation import check_is_fitted

from .schema import MODEL_FIELDS, PatientIntake, normalize_key

NUMERIC_FEATURES = [
    "age", "height_cm", "weight_kg", "pulse", "systolic_bp", "diastolic_bp",
    "respiratory_rate", "temperature_c", "spo2", "pain_score",
]
CATEGORICAL_FEATURES = ["blood_type"]
TEXT_FEATURES = ["chief_complaint", "chronic_conditions", "regular_medications"]
FEATURE_COLUMNS = list(MODEL_FIELDS)

URGENCY_LABELS = {
    1: "Not urgent",
    2: "Low urgency",
    3: "Moderate urgency",
    4: "Urgent",
    5: "Very urgent",
}

NON_CLINIC_SPECIALTIES = {
    normalize_key(label)
    for label in (
        "Autopsy",
        "Consult - History and Phy.",
        "Discharge Summary",
        "Emergency Room Reports",
        "IME-QME-Work Comp etc.",
        "Lab Medicine - Pathology",
        "Letters",
        "Office Notes",
        "SOAP / Chart / Progress Notes",
    )
}


@dataclass
class TriagePrediction:
    urgency_level: int
    urgency_label: str
    confidence: float
    probabilities: dict[int, float]


def _combine_text(frame: Any) -> list[str]:
    if isinstance(frame, pd.Series):
        frame = frame.to_frame()
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame, columns=TEXT_FEATURES)
    cleaned = frame.reindex(columns=TEXT_FEATURES).fillna("").astype(str)
    return cleaned.agg(" ".join, axis=1).tolist()


def _feature_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    normalized = [PatientIntake.from_mapping(row).to_model_dict() for row in rows]
    frame = pd.DataFrame(normalized, columns=FEATURE_COLUMNS)
    for field in TEXT_FEATURES:
        frame[field] = frame[field].fillna("").astype(str)
    return frame


def _build_pipeline() -> Pipeline:
    text_pipeline = Pipeline([
        ("combine", FunctionTransformer(_combine_text, validate=False)),
        ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
    ])
    features = ColumnTransformer(
        transformers=[
            ("numeric", SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True), NUMERIC_FEATURES),
            ("blood_type", Pipeline([
                ("impute", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]), CATEGORICAL_FEATURES),
            ("clinical_text", text_pipeline, TEXT_FEATURES),
        ],
        remainder="drop",
    )
    return Pipeline([
        ("features", features),
        ("classifier", RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )),
    ])


class UrgencyClassifier:
    """Train on explicit 1–5 urgency labels or inverted FedMML ESI labels."""

    def __init__(self, pipeline: Pipeline | None = None):
        self.pipeline = pipeline or _build_pipeline()

    @classmethod
    def train_from_csv(cls, csv_path: str) -> "UrgencyClassifier":
        return cls().fit(pd.read_csv(csv_path))

    @staticmethod
    def _target_column(columns: list[Any]) -> tuple[Any | None, bool]:
        names = {normalize_key(column): column for column in columns}
        urgency_names = {
            "urgency level", "urgency_level", "aciliyet seviyesi", "aciliyet",
            "triage level", "triage_level",
        }
        for name in urgency_names:
            normalized = normalize_key(name)
            if normalized in names:
                return names[normalized], False
        if "esi level" in names:
            return names["esi level"], True
        return None, False

    @classmethod
    def prepare_training_data(
        cls, encounters: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.Series]:
        target_column, invert_esi = cls._target_column(list(encounters.columns))
        if target_column is None:
            if any(normalize_key(column) in {"patient status", "hasta durumu", "status"} for column in encounters.columns):
                raise ValueError(
                    "Color-coded patient status labels are not exact 1–5 targets. "
                    "Provide an 'urgency_level' (1–5) column for each encounter, or use 'esi_level'."
                )
            raise ValueError("Training data needs an 'urgency_level' (1–5) or 'esi_level' target column.")

        targets = pd.to_numeric(encounters[target_column], errors="coerce")
        if invert_esi:
            targets = 6 - targets
        valid = targets.notna() & targets.isin([1, 2, 3, 4, 5])
        if not valid.any():
            raise ValueError("No valid urgency targets (1–5) were found.")
        return encounters.loc[valid].copy(), targets.loc[valid].astype(int)

    def fit(self, encounters: pd.DataFrame) -> "UrgencyClassifier":
        valid_encounters, labels = self.prepare_training_data(encounters)
        rows = valid_encounters.to_dict(orient="records")
        self.pipeline.fit(_feature_frame(rows), labels)
        return self

    def predict(self, intake: PatientIntake | dict[str, Any]) -> TriagePrediction:
        try:
            check_is_fitted(self.pipeline)
        except Exception as error:
            raise RuntimeError("Classifier is not trained. Call fit() before predict().") from error
        if isinstance(intake, PatientIntake):
            values = intake.to_dict()
        elif hasattr(intake, "model_dump"):
            values = intake.model_dump()
        elif hasattr(intake, "dict"):
            values = intake.dict()
        else:
            values = intake
        frame = _feature_frame([values])
        level = int(self.pipeline.predict(frame)[0])
        predicted = self.pipeline.predict_proba(frame)[0]
        probabilities = {
            int(class_id): float(probability)
            for class_id, probability in zip(self.pipeline.classes_, predicted)
        }
        return TriagePrediction(
            urgency_level=level,
            urgency_label=URGENCY_LABELS[level],
            confidence=probabilities[level],
            probabilities=probabilities,
        )

    def save(self, path: str) -> None:
        import joblib

        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, path: str) -> "UrgencyClassifier":
        import joblib

        return cls(joblib.load(path))


@dataclass
class SpecialtyCandidate:
    specialty: str
    confidence: float


@dataclass
class SpecialtyPrediction:
    candidates: list[SpecialtyCandidate]


class ClinicalSpecialtyClassifier:
    """Suggest medical specialties from the Kaggle MTSamples transcription data."""

    def __init__(self, pipeline: Pipeline | None = None):
        self.pipeline = pipeline or Pipeline([
            ("text", TfidfVectorizer(
                max_features=100_000,
                ngram_range=(1, 2),
                min_df=2,
                stop_words="english",
                sublinear_tf=True,
            )),
            ("classifier", LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=42,
            )),
        ])

    @classmethod
    def train_from_csv(
        cls,
        csv_path: str,
        *,
        minimum_samples_per_specialty: int = 8,
    ) -> "ClinicalSpecialtyClassifier":
        return cls().fit(
            pd.read_csv(csv_path),
            minimum_samples_per_specialty=minimum_samples_per_specialty,
        )

    @classmethod
    def prepare_training_data(
        cls,
        records: pd.DataFrame,
        *,
        minimum_samples_per_specialty: int = 8,
    ) -> tuple[pd.Series, pd.Series]:
        columns = {normalize_key(column): column for column in records.columns}
        label_column = next(
            (columns[name] for name in ("medical specialty", "specialty", "clinic", "department") if name in columns),
            None,
        )
        transcription_column = next(
            (columns[name] for name in ("transcription", "clinical text", "text") if name in columns),
            None,
        )
        description_column = columns.get("description")
        if label_column is None or transcription_column is None:
            raise ValueError(
                "The specialty dataset must contain 'medical_specialty' and 'transcription' columns."
            )

        labels = records[label_column].fillna("").astype(str).str.strip()
        transcription = records[transcription_column].fillna("").astype(str).str.strip()
        if description_column is not None:
            description = records[description_column].fillna("").astype(str).str.strip()
            texts = (description + " " + transcription).str.strip()
        else:
            texts = transcription

        counts = labels.value_counts()
        eligible = counts[counts >= minimum_samples_per_specialty].index
        valid = (
            labels.isin(eligible)
            & texts.ne("")
            & labels.ne("")
            & ~labels.map(normalize_key).isin(NON_CLINIC_SPECIALTIES)
        )
        if labels.loc[valid].nunique() < 2:
            raise ValueError(
                "At least two specialties with enough labeled transcriptions are required."
            )
        return texts.loc[valid], labels.loc[valid]

    def fit(
        self,
        records: pd.DataFrame,
        *,
        minimum_samples_per_specialty: int = 8,
    ) -> "ClinicalSpecialtyClassifier":
        texts, labels = self.prepare_training_data(
            records,
            minimum_samples_per_specialty=minimum_samples_per_specialty,
        )
        self.pipeline.fit(texts, labels)
        return self

    def predict(self, text: str, *, top_k: int = 3) -> SpecialtyPrediction:
        try:
            check_is_fitted(self.pipeline)
        except Exception as error:
            raise RuntimeError("Specialty classifier is not trained. Call fit() before predict().") from error
        if not text.strip():
            return SpecialtyPrediction(candidates=[])
        probabilities = self.pipeline.predict_proba([text])[0]
        classes = self.pipeline.classes_
        ranked = sorted(
            zip(classes, probabilities),
            key=lambda item: float(item[1]),
            reverse=True,
        )[: max(1, top_k)]
        return SpecialtyPrediction([
            SpecialtyCandidate(specialty=str(label), confidence=float(score))
            for label, score in ranked
        ])

    def save(self, path: str) -> None:
        import joblib

        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, path: str) -> "ClinicalSpecialtyClassifier":
        import joblib

        return cls(joblib.load(path))


ESIClassifier = UrgencyClassifier
ESIPrediction = TriagePrediction
