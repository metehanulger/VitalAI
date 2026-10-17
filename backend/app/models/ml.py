"""ESI urgency classifier trained on the FedMML ED triage CSV.

This model predicts only the dataset's ESI label. The dataset has no destination
department label, so it cannot train or validate specialty referral decisions.
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.validation import check_is_fitted

from .schema import PatientIntake

NUMERIC_FEATURES = [
    "age",
    "systolic_bp",
    "diastolic_bp",
    "heart_rate",
    "respiratory_rate",
    "temperature",
    "spo2",
    "pain_score",
    "wbc",
    "hemoglobin",
    "platelet_count",
    "sodium",
    "potassium",
    "creatinine",
    "glucose",
    "troponin",
    "bnp",
    "lactate",
    "inr",
]
TEXT_FEATURES = ["chief_complaint", "clinical_notes"]
FEATURE_COLUMNS = NUMERIC_FEATURES + ["sex"] + TEXT_FEATURES

ESI_URGENCY = {
    1: "Immediate: resuscitation-level acuity",
    2: "Emergent: high-risk or time-sensitive acuity",
    3: "Urgent: needs prompt emergency department assessment",
    4: "Less urgent: lower acuity",
    5: "Non-urgent: lowest acuity in this scale",
}


@dataclass
class ESIPrediction:
    esi_level: int
    urgency: str
    confidence: float
    probabilities: dict[int, float]
    department: None = None
    department_note: str = (
        "The source dataset contains no department destination label. "
        "A qualified clinician must determine the appropriate department."
    )


def _clean_text(values: Any) -> list[str]:
    if isinstance(values, pd.DataFrame):
        series = values.iloc[:, 0]
    elif isinstance(values, pd.Series):
        series = values
    else:
        series = pd.Series(values)
    return series.fillna("").astype(str).tolist()


def _feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in FEATURE_COLUMNS:
        if column not in result:
            result[column] = None
    for column in TEXT_FEATURES:
        result[column] = result[column].fillna("").astype(str)
    return result[FEATURE_COLUMNS]


def _build_pipeline() -> Pipeline:
    text_pipeline = Pipeline(
        [
            ("clean", FunctionTransformer(_clean_text, validate=False)),
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
        ]
    )
    features = ColumnTransformer(
        transformers=[
            ("numeric", SimpleImputer(strategy="median", add_indicator=True), NUMERIC_FEATURES),
            ("sex", Pipeline([
                ("impute", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]), ["sex"]),
            ("complaint", text_pipeline, "chief_complaint"),
            ("notes", text_pipeline, "clinical_notes"),
        ],
        remainder="drop",
    )
    return Pipeline(
        [
            ("features", features),
            ("classifier", RandomForestClassifier(
                n_estimators=300,
                class_weight="balanced_subsample",
                random_state=42,
                n_jobs=-1,
            )),
        ]
    )


class ESIClassifier:
    """Train and use the ESI classifier; input may omit any measurement."""

    def __init__(self, pipeline: Pipeline | None = None):
        self.pipeline = pipeline or _build_pipeline()

    @classmethod
    def train_from_csv(cls, csv_path: str) -> "ESIClassifier":
        """Load a locally available dataset CSV and fit the classifier."""
        return cls().fit(pd.read_csv(csv_path))

    def fit(self, encounters: pd.DataFrame) -> "ESIClassifier":
        if "esi_level" not in encounters.columns:
            raise ValueError("Training data must include the 'esi_level' target column.")
        labels = pd.to_numeric(encounters["esi_level"], errors="coerce")
        valid = labels.notna() & labels.isin([1, 2, 3, 4, 5])
        if not valid.any():
            raise ValueError("No valid ESI labels (1–5) were found.")
        self.pipeline.fit(_feature_frame(encounters.loc[valid]), labels.loc[valid].astype(int))
        return self

    def predict(self, intake: PatientIntake | dict[str, Any]) -> ESIPrediction:
        try:
            check_is_fitted(self.pipeline)
        except Exception as error:
            raise RuntimeError("Classifier is not trained. Call fit() before predict().") from error
        values = intake.to_dict() if isinstance(intake, PatientIntake) else intake
        frame = _feature_frame(pd.DataFrame([values]))
        label = int(self.pipeline.predict(frame)[0])
        class_probabilities = self.pipeline.predict_proba(frame)[0]
        probabilities = {
            int(class_id): float(probability)
            for class_id, probability in zip(self.pipeline.classes_, class_probabilities)
        }
        return ESIPrediction(
            esi_level=label,
            urgency=ESI_URGENCY[label],
            confidence=probabilities[label],
            probabilities=probabilities,
        )

    def save(self, path: str) -> None:
        import joblib

        joblib.dump(self.pipeline, path)

    @classmethod
    def load(cls, path: str) -> "ESIClassifier":
        import joblib

        return cls(joblib.load(path))
