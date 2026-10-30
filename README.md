<div align="center">

# VitialAI · Emergency Pre-Triage & Department Routing

**Collect patient intake details, estimate urgency, and manage the daily triage queue.**

React · FastAPI · PostgreSQL

</div>

<p align="center">
  <a href="#overview">Overview</a> ·
  <a href="#how-a-triage-decision-is-made">Decision flow</a> ·
  <a href="#features">Features</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#configuration">Configuration</a> ·
  <a href="#api-reference">API</a> ·
  <a href="#training-the-local-ml-models-optional">ML models</a>
</p>

## Overview

VitialAI is an **emergency department pre-triage demonstration**. It collects demographics, medical history, vital signs, and the patient's chief complaint. The backend combines NEWS2-based rules, optional local machine-learning models, and an optional configured LLM provider to produce a triage result.

Each result includes a color-coded status, an urgency score from 1 to 5, a suggested department, and an explanation. Records are stored in a database and shown in the daily queue and history views. If the LLM or local model artifacts are unavailable, the rules-based assessment can still run.

> **Clinical use notice:** This project is for education and software demonstration only. It is not intended for diagnosis or treatment, has not been clinically validated, and does not replace assessment by a qualified healthcare professional.

## How a triage decision is made

1. **Rules.** The backend calculates NEWS2 from the vital signs, including ACVPU consciousness and supplemental oxygen. It also checks the complaint for critical and urgent symptoms in Turkish and English, and ignores symptoms the patient denies, such as "göğüs ağrısı yok". The result is a minimum color category that nothing later can lower.
2. **Complaint normalization.** When the ML models are available, one short LLM call translates the complaint into English and maps it onto one of the 28 complaint categories the urgency model was trained on.
3. **Two ML models.** The urgency model (FedMML) predicts a 1 to 5 urgency level. The specialty model (MTSamples) suggests departments, which are mapped onto the hospital's department list.
4. **LLM decision.** The LLM receives the four intake cards, the NEWS2 score, the ML signals, and the disease-to-department reference table. It answers in a fixed JSON schema and may choose only listed departments.
5. **Safety merge.** The final category is the most urgent of the rules and the LLM, so the AI can raise urgency but never lower it. Patients older than 64 are raised by one level.
6. **Fallbacks.** If an LLM model fails, the next configured Gemini model is tried. If no LLM answers, the rules decide the category and a keyword router picks the department.

## Features

- Four-part patient intake: demographics, medical history, vital signs, and chief complaint
- Rules-based prioritization using NEWS2 (including ACVPU consciousness and supplemental oxygen) and Turkish and English symptom checks that ignore denied symptoms
- Department routing from a closed, configurable department list, with keyword routing when no LLM is available
- Optional OpenAI-compatible API, Google Gemini, or IBM watsonx.ai integration, with structured JSON output and automatic Gemini model fallback
- Optional local classifiers trainable with the FedMML and MTSamples datasets
- Daily patient queue, paginated record history, and triage details with key findings, early-warning notes, and alternative departments
- Evaluation script for under-triage, over-triage, and department accuracy on labeled cases
- PostgreSQL storage for local development and the Docker Compose setup
- Turkish national ID and passport validation; ID numbers are masked in API responses

## Technology stack

| Layer | Technologies |
|---|---|
| Web app | React 18, Vite, Tailwind CSS |
| API | Python 3.12, FastAPI, Pydantic |
| Database | PostgreSQL 17 (psycopg 3 driver, SQLAlchemy 2) |
| Machine learning | pandas, scikit-learn, joblib |
| LLM providers | OpenAI-compatible REST API, Google Gemini, IBM watsonx.ai |

## Quick start

### Requirements

- Python 3.12 (64-bit recommended)
- Node.js and npm
- Git
- PostgreSQL 14 or newer, or Docker Desktop to run PostgreSQL with Docker Compose

### 1. Start PostgreSQL

The easiest option is to start only the database container from the repository root:

```bash
docker compose up -d postgres
```

This creates the `triajdb` database with user `triaj` and password `triaj_sifre`. The backend builds the schema itself when it starts. To use your own PostgreSQL server instead, create a database and set `DATABASE_URL` in `backend/.env`.

### 2. Start the backend

On Windows, in PowerShell from the repository root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install uv
uv sync --group dev
uv run uvicorn app.main:app --reload
```

On macOS or Linux, from the repository root:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip uv
uv sync --group dev
uv run uvicorn app.main:app --reload
```

The backend connects to `postgresql+psycopg://triaj:triaj_sifre@localhost:5432/triajdb` by default. On startup it applies the Alembic migrations, which create the tables and load the disease-to-clinic reference data. It also loads the local ML models at startup, so the first triage request is not slowed down. The API is available at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

> If PowerShell blocks virtual environment activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then retry the activation command.

### 3. Start the web app

Open a second terminal at the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Vite usually serves the app at `http://localhost:5173` and proxies `/api` requests to the backend at `http://127.0.0.1:8000`.

## Configuration

The application reads settings from a `.env` file in the repository root or in `backend/`. Use `backend/.env.example` as a starting point.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL SQLAlchemy URL. The default is `postgresql+psycopg://triaj:triaj_sifre@localhost:5432/triajdb`. Other database engines are rejected at startup. |
| `DB_AUTO_MIGRATE` | Apply Alembic migrations on startup (default `true`). Set `false` to run `uv run alembic upgrade head` yourself. |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | SQLAlchemy connection pool size (defaults: 5 and 10). |
| `LLM_PROVIDER` | `openai_compatible`, `gemini`, or `watsonx` |
| `LLM_API_KEY` | API key for an OpenAI-compatible provider |
| `LLM_BASE_URL` | OpenAI-compatible API base URL; defaults to `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name for the OpenAI-compatible provider |
| `LLM_TIMEOUT_SECONDS` | Request timeout for the main triage call (default 30) |
| `LLM_TRANSLATION_TIMEOUT_SECONDS` | Shorter timeout for the complaint normalization call that feeds both ML models (default 15) |
| `POLIKLINIKLER` | Comma-separated English department names the triage may recommend. Empty uses the default list in `backend/app/core/poliklinikler.py`. Emergency Medicine is always included. |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | API key and model when using Gemini (google-genai SDK) |
| `GEMINI_FALLBACK_MODELS` | Comma-separated Gemini models tried in order when the primary model fails because of quota, unavailability, or a timeout. A failing model is skipped for a while, so later requests go straight to a working one. Free-tier quotas are counted per model. |
| `GEMINI_TIMEOUT_SECONDS` | Gemini request timeout (default 60). A whole Gemini call, including fallbacks, is capped at 1.5 times this value. |
| `WATSONX_API_KEY` / `WATSONX_PROJECT_ID` | Credentials when using IBM watsonx.ai |
| `TRIAGE_URGENCY_MODEL` / `TRIAGE_SPECIALTY_MODEL` | Optional paths to trained local model files |

All settings are defined in `backend/app/core/config.py`. Environment variables take priority over `.env` files. With no LLM credentials configured, the rules-based assessment remains available, but LLM-generated analysis is disabled.

To enable Gemini during local development, copy the example file to `backend/.env` before starting the backend and add your own key:

```powershell
# Windows PowerShell, from the repository root
Copy-Item backend/.env.example backend/.env
```

```bash
# macOS or Linux, from the repository root
cp backend/.env.example backend/.env
```

Then open `backend/.env`, set `GEMINI_API_KEY` to your key, and save it. Keep this personal file private; it is ignored by Git. Without a key, the app still runs with rules-based assessment.

The `uv.lock` file pins the backend dependency graph across supported platforms. Google Gemini support is included in the standard backend install. Set `GEMINI_API_KEY` in `.env` to enable it. From `backend/`, add other optional integrations only when needed:

| Need | Install |
|---|---|
| IBM watsonx.ai | `uv sync --extra llm` |

The PostgreSQL driver (`psycopg`) is part of the standard install. The backend Docker image also installs the watsonx.ai extra.

### Running the tests

The tests drop and recreate all tables, so they use a separate database whose name must contain `test`. Create it once, then run the tests from `backend/`:

```bash
docker compose exec postgres createdb -U triaj triajdb_test
uv run pytest
```

Set `TEST_DATABASE_URL` to use a different test database. The default is `postgresql+psycopg://triaj:triaj_sifre@localhost:5432/triajdb_test`.

### Evaluating triage quality

`backend/app/evaluation/degerlendir.py` runs labeled cases through the triage engine and reports the under-triage rate, over-triage rate, status accuracy, department top-1 and top-3 accuracy, and how often the LLM answered. Cases use the columns of `backend/evaluation/vakalar_ornek.csv`. That file is only a format sample; its labels are not clinically validated, so replace them with cases labeled by nurses or physicians before drawing conclusions. From `backend/`:

```bash
uv run python -m app.evaluation.degerlendir --vakalar evaluation/vakalar_ornek.csv --llm-yok
uv run python -m app.evaluation.degerlendir --vakalar evaluation/vakalar_ornek.csv --bekleme 30 --cikti sonuclar.csv
```

`--llm-yok` evaluates the rules and ML models only. `--bekleme` waits between cases to stay within rate limits; each case makes up to two LLM calls.

### Changing the database schema

The SQLAlchemy models in `backend/app/db/tables.py` define the schema. After changing a model, generate and review a migration from `backend/`:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

A test fails if the models and migrations drift apart.

### Docker Compose

From the repository root:

```powershell
docker compose up --build
```

Compose starts PostgreSQL, the backend, and the frontend. When the backend starts, it applies the Alembic migrations to create or update the schema. Compose sets `DATABASE_URL` for the backend. Override the credentials with `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`. To remove the persisted PostgreSQL data as well as stop the containers, run `docker compose down -v`.

The frontend is available at `http://localhost:5173`, and the API at `http://localhost:8000`. If you trained local ML models, Compose mounts `backend/model_artifacts/` into the backend container as read-only; without artifacts, the rules-based assessment remains available.

## API reference

All endpoints use the base URL `http://localhost:8000`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/triage` | Create a triage record and return its result (`201`) |
| `GET` | `/api/triage` | List the daily queue; supports `tarih`, `durum`, and `limit` query parameters |
| `GET` | `/api/triage/{log_id}` | Get a result and all four intake sections |
| `GET` | `/api/triage/history` | List saved records, newest first; supports `limit` (default 50, maximum 500) and `offset`. The total count is in the `X-Total-Count` header. |
| `PATCH` | `/api/triage/{log_id}` | Update a record's color-coded status |
| `GET` | `/api/triage/secenekler` | Get the form options |
| `GET` | `/api/health` | Check API and database availability |

The API field names are Turkish. Example `POST /api/triage` request:

```json
{
  "demografi": {
    "isim": "Alex Morgan",
    "yas": 34,
    "boy": 165,
    "kilo": 60.5,
    "kan_grubu": "A+",
    "kimlik_turu": "PASAPORT",
    "kimlik_no": "A1234567"
  },
  "tibbi_gecmis": {
    "kronik_rahatsizlik": "Asthma",
    "surekli_ilac": ""
  },
  "vitaller": {
    "nabiz": 78,
    "tansiyon_sistolik": 120,
    "tansiyon_diyastolik": 80,
    "solunum": 16,
    "ates": 36.8,
    "spo2": 98,
    "bilinc": "A",
    "ek_oksijen": false
  },
  "sikayet": {
    "ana_sikayet": "Sore throat",
    "agri_skalasi": 3
  }
}
```

Example response (`201 Created`):

```json
{
  "log_id": 12,
  "sira_no": 7,
  "tarih": "2026-10-19",
  "saat": "15:42:10",
  "hasta_durumu": "YESIL",
  "risk_skoru": 5,
  "aciliyet_seviyesi": 1,
  "onerilen_poliklinik": "Otolaryngology",
  "aciklama": "Vital signs are stable; no urgent risk was identified.",
  "karar_kaynagi": "KURAL",
  "kodlar": {
    "demografi_id": 12,
    "tibbi_gecmis_id": 12,
    "vitaller_id": 12,
    "sikayet_id": 12
  },
  "kritik_bulgu": "Vital signs are stable; no urgent risk was identified.",
  "erken_uyari_notu": "Model-based triage was unavailable; a nurse or physician must review this result.",
  "news2_skoru": 0,
  "birim_uyumluluk_siralamasi": [
    {"birim": "Otolaryngology", "uyum_skoru": 1.0, "gerekce": "Matched the reported symptoms."}
  ]
}
```

### Understanding the scores

- `risk_skoru` follows the ESI direction: **1 is most urgent**, **5 is least urgent**.
- `aciliyet_seviyesi` is the reversed project scale shown in the UI: **1 is least urgent**, **5 is most urgent**.
- Color-coded statuses are `KIRMIZI` (red), `SARI` (yellow), and `YESIL` (green).
- For patients aged 65 or older, the final urgency is increased by one level.
- `bilinc` is the ACVPU consciousness level: `A` alert, `C` new confusion, `V` responds to voice, `P` responds to pain, `U` unresponsive. `P` and `U` always give `KIRMIZI`. `ek_oksijen` marks supplemental oxygen. Both default to a normal value when omitted.
- A manual status change with `PATCH` also moves `risk_skoru` into the new status's range, so the queue order follows the staff decision.
- National ID and passport numbers are masked in API responses. Do not send real personal or health information to public environments.

## Training the local ML models (optional)

Training CSV files are included under `backend/data/`. From the `backend/` directory, run:

```bash
python -m app.models.train \
  --fedmml ./data/fedmml.csv \
  --mtsamples ./data/mtsamples.csv
```

Training prints classification metrics and saves the models to `backend/model_artifacts/`. These generated files are ignored by Git. Performance on the source datasets is not independent clinical validation. See the [model notes](backend/app/models/README.md) for dataset sources, licenses, and limitations.

## Repository structure

```text
backend/
  app/api/       FastAPI endpoints
  app/core/      Triage rules, LLM clients, and configuration
  app/db/        SQLAlchemy models (the schema definition) and data access
  app/models/    Data models and ML classifiers
  app/evaluation/ Triage quality evaluation script
  migrations/    Alembic database migrations
  evaluation/    Example labeled-case file for the evaluation script
  pyproject.toml Python dependency and optional integration definitions
  uv.lock        Locked Python dependency versions
  data/          Model training datasets
  tests/         Backend tests
frontend/        React web app and its Docker/nginx configuration
docker-compose.yml
```

## Latest changes

- **PostgreSQL only.** IBM Db2 and SQLite were removed. Alembic migrations now build the schema and load the reference data, and database limits match the form limits, so critical values such as SpO2 35% are stored instead of rejected.
- **Reliable queue numbers.** A PostgreSQL advisory lock gives concurrent registrations distinct, consecutive queue numbers without retries.
- **Better decisions.** The LLM now sees the diastolic pressure, which was previously missing from its input, along with the NEWS2 score and the reference table. Its output is validated against a fixed schema and a closed department list.
- **Working ML signals.** The urgency model receives the mapped complaint category instead of untranslated text it could not read, and the specialty model's labels are mapped onto real departments.
- **Safer rules.** Denied symptoms are ignored, Turkish word forms are recognized, stroke signs and airway swelling are caught, and false matches such as "burnum" (my nose) for "burn" are avoided. NEWS2 now includes consciousness and supplemental oxygen.
- **Resilient LLM use.** The client uses the google-genai SDK, reuses provider clients, falls back across Gemini models, and skips a failing model for a while.
- **Faster and leaner.** ML models load at startup, urgency scoring is about four times faster, history is paginated, and the health check no longer counts every record.
- **More useful results.** The API and the web app show key findings, early-warning notes, NEWS2, and alternative departments.

## License

The code is distributed under the [MIT License](LICENSE). Dataset source and license information is documented in the [model notes](backend/app/models/README.md).
