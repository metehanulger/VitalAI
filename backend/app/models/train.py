"""Train the triage urgency and medical-specialty models from local CSV files."""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split

from .ml import (
    URGENCY_LABELS,
    ClinicalSpecialtyClassifier,
    UrgencyClassifier,
    _feature_frame,
)


def _print_metrics(
    title: str,
    actual: pd.Series,
    predicted,
    *,
    labels: list,
    target_names: list[str],
) -> None:
    print(f"\n{title} (held-out test split, {len(actual)} rows)")
    print(f"Accuracy: {accuracy_score(actual, predicted):.3f}")
    print(f"Balanced accuracy: {balanced_accuracy_score(actual, predicted):.3f}")
    print(f"Macro F1: {f1_score(actual, predicted, labels=labels, average='macro', zero_division=0):.3f}")
    print(classification_report(
        actual,
        predicted,
        labels=labels,
        target_names=target_names,
        zero_division=0,
        digits=3,
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fedmml", required=True, help="Path to the FedMML triage CSV")
    parser.add_argument("--mtsamples", required=True, help="Path to the MTSamples CSV")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[2] / "model_artifacts"),
        help="Directory where trained model files will be saved",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of each dataset reserved for stratified evaluation (default: 0.2)",
    )
    args = parser.parse_args()
    if not 0 < args.test_size < 1:
        parser.error("--test-size must be between 0 and 1")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fedmml = pd.read_csv(args.fedmml)
    urgency_rows, urgency_targets = UrgencyClassifier.prepare_training_data(fedmml)
    urgency_train_index, urgency_test_index = train_test_split(
        urgency_rows.index,
        test_size=args.test_size,
        random_state=42,
        stratify=urgency_targets,
    )

    urgency_evaluation_model = UrgencyClassifier().fit(urgency_rows.loc[urgency_train_index])
    urgency_test_features = _feature_frame(
        urgency_rows.loc[urgency_test_index].to_dict(orient="records")
    )
    urgency_predictions = urgency_evaluation_model.pipeline.predict(urgency_test_features)
    urgency_test_targets = urgency_targets.loc[urgency_test_index]
    _print_metrics(
        "Urgency model",
        urgency_test_targets,
        urgency_predictions,
        labels=[1, 2, 3, 4, 5],
        target_names=[f"{level} - {URGENCY_LABELS[level]}" for level in range(1, 6)],
    )

    specialty_records = pd.read_csv(args.mtsamples)
    specialty_texts, specialty_targets = ClinicalSpecialtyClassifier.prepare_training_data(
        specialty_records
    )
    specialty_train_texts, specialty_test_texts, specialty_train_targets, specialty_test_targets = train_test_split(
        specialty_texts,
        specialty_targets,
        test_size=args.test_size,
        random_state=42,
        stratify=specialty_targets,
    )
    specialty_evaluation_model = ClinicalSpecialtyClassifier()
    specialty_evaluation_model.pipeline.fit(specialty_train_texts, specialty_train_targets)
    specialty_predictions = specialty_evaluation_model.pipeline.predict(specialty_test_texts)
    specialty_labels = sorted(specialty_targets.unique().tolist())
    _print_metrics(
        "Specialty model",
        specialty_test_targets,
        specialty_predictions,
        labels=specialty_labels,
        target_names=specialty_labels,
    )

    urgency_model = UrgencyClassifier().fit(fedmml)
    urgency_path = output_dir / "urgency.joblib"
    urgency_model.save(str(urgency_path))

    specialty_model = ClinicalSpecialtyClassifier().fit(specialty_records)
    specialty_path = output_dir / "specialty.joblib"
    specialty_model.save(str(specialty_path))

    print(f"Saved urgency model: {urgency_path}")
    print(f"Saved specialty model: {specialty_path}")


if __name__ == "__main__":
    main()
