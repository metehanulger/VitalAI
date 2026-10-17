# Model training

The service trains two separate classifiers because the source datasets have
different labels:

- FedMML trains the urgency classifier from `esi_level` and triage features.
- MTSamples trains the specialty classifier from medical transcription text and
  `medical_specialty` labels. Non-clinic document categories are excluded.

Download the CSV files locally after accepting the source dataset access terms.
The triage source is [FedMML ED Triage](https://huggingface.co/datasets/olaflaitinen/fedmml-ed-triage).
The Kaggle notebook uses the [MTSamples medical transcription data](https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions).
Place both CSVs in a local data directory, then run this from `backend/`:

## Dataset sources and licenses

- **FedMML ED Triage:** The dataset card identifies the records as synthetic and
  licenses the dataset under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  If redistributing the CSV, retain attribution to Gustav Olaf Yunus Laitinen-Fredriksson
  Lundström-Imanov and Sila Burde Dulger and cite the [dataset card](https://huggingface.co/datasets/olaflaitinen/fedmml-ed-triage).
  The Hugging Face repository also requires accepting its access conditions.
- **MTSamples Medical Transcriptions:** The [Kaggle dataset page](https://www.kaggle.com/datasets/tboyle10/medicaltranscriptions)
  lists the data under CC0: Public Domain and credits Tara Boyle; its source is
  [MTSamples.com](https://www.mtsamples.com/).

These terms apply to the source datasets, not to this project's code. Never include
locally collected patient records, `.env` files, or API keys in a public repository.

```bash
python -m app.models.train \
  --fedmml ./data/fedmml.csv \
  --mtsamples ./data/mtsamples.csv
```

Training first reserves a stratified 20% holdout from each dataset and prints
accuracy, balanced accuracy, macro F1, and per-class precision/recall. It then
trains the saved artifacts on the full datasets. Change the holdout fraction with
`--test-size 0.25`. Macro F1 and per-class recall are useful alongside accuracy
because both datasets have uneven class counts.

The generated artifacts are saved under `backend/model_artifacts/` by default and
are loaded by the triage API on its first request. Override their locations with
`TRIAGE_URGENCY_MODEL` and `TRIAGE_SPECIALTY_MODEL` if needed.
Restart the API after training so a process that already cached missing artifacts
can load the new files.

The reported scores are a random holdout from these source datasets, not an
independent clinical validation. The urgency model uses the fields shared with the intake form: age, chief
complaint, pulse, blood pressure, respiratory rate, temperature, SpO2, and pain
score. Features absent from FedMML, such as height, weight, blood type, and medical
history, cannot be learned from that dataset. The MTSamples model is trained on
English clinician transcriptions while the intake is a short patient complaint.
When the specialty artifact is loaded, the configured LLM translates the complaint
and brief medical history into English before classification. This adds one short
LLM call per triage request. Specialty predictions are advisory and are withheld
from the final LLM context when the top class probability is below 0.30. Validate
both models on representative, clinician-reviewed data before any use beyond a
software demonstration.
