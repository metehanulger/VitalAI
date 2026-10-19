<div align="center">

# VitialAI · Emergency Pre-Triage & Department Routing

**Collect patient intake details, estimate urgency, and manage the daily triage queue.**

React · FastAPI · SQLite, PostgreSQL, or IBM Db2

</div>

<p align="center">
  <a href="#overview">Overview</a> ·
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

## Features

- Four-part patient intake: demographics, medical history, vital signs, and chief complaint
- Rules-based prioritization using NEWS2 and critical-symptom checks
- Optional OpenAI-compatible API, Google Gemini, or IBM watsonx.ai integration
- Optional local classifiers trainable with the FedMML and MTSamples datasets
- Daily patient queue, saved-record history, and triage details
- SQLite for local development, configurable PostgreSQL, and Db2 in the Docker Compose setup
- Turkish national ID and passport validation; ID numbers are masked in API responses

## Technology stack

| Layer | Technologies |
|---|---|
| Web app | React 18, Vite, Tailwind CSS |
| API | Python 3.12, FastAPI, Pydantic |
| Database | SQLite (local default), PostgreSQL, IBM Db2 (Compose configuration) |
| Machine learning | pandas, scikit-learn, joblib |
| LLM providers | OpenAI-compatible REST API, Google Gemini, IBM watsonx.ai |

## Quick start

### Requirements

- Python 3.12 (64-bit recommended)
- Node.js and npm
- Git
- Optional: Docker Desktop (for Db2 with Docker Compose)

### 1. Start the backend

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

The local default database is SQLite, so no separate database server is needed. Tables are created automatically when the backend starts. The API is available at `http://localhost:8000`; interactive API documentation is at `http://localhost:8000/docs`.

> If PowerShell blocks virtual environment activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then retry the activation command.

### 2. Start the web app

Open a second terminal at the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Vite usually serves the app at `http://localhost:5173` and proxies `/api` requests to the backend at `http://127.0.0.1:8000`.

## Configuration

The application reads settings from a `.env` file in the repository root or in `backend/`. Use `backend/.env.example` as a starting point. Local development uses SQLite and needs no separate database server.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy connection URL. The local default is `sqlite:///./triaj.db`. |
| `LLM_PROVIDER` | `openai_compatible`, `gemini`, or `watsonx` |
| `LLM_API_KEY` | API key for an OpenAI-compatible provider |
| `LLM_BASE_URL` | OpenAI-compatible API base URL; defaults to `https://api.openai.com/v1` |
| `LLM_MODEL` | Model name for the OpenAI-compatible provider |
| `GEMINI_API_KEY` | API key when using Gemini |
| `WATSONX_API_KEY` / `WATSONX_PROJECT_ID` | Credentials when using IBM watsonx.ai |
| `TRIAGE_URGENCY_MODEL` / `TRIAGE_SPECIALTY_MODEL` | Optional paths to trained local model files |

With no LLM credentials configured, the rules-based assessment remains available, but LLM-generated analysis is disabled. Db2 settings are not needed unless you use the Db2 Compose setup.

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
| PostgreSQL | `uv sync --extra postgres` |
| IBM Db2 | `uv sync --extra db2` |

The Db2 Docker image installs the Db2 and LLM extras automatically. The basic Windows/SQLite setup does not install optional database drivers.

### Docker Compose with Db2

From the repository root:

```powershell
docker compose up --build
```

Compose starts the backend and IBM Db2. Initial Db2 setup can take several minutes. Compose sets `DATABASE_URL` for the Db2 connection. To remove the persisted Db2 data as well as stop the containers, run `docker compose down -v`.

The frontend is available at `http://localhost:5173`, and the API at `http://localhost:8000`. If you trained local ML models, Compose mounts `backend/model_artifacts/` into the backend container as read-only; without artifacts, the rules-based assessment remains available.

## API reference

All endpoints use the base URL `http://localhost:8000`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/triage` | Create a triage record and return its result (`201`) |
| `GET` | `/api/triage` | List the daily queue; supports `tarih`, `durum`, and `limit` query parameters |
| `GET` | `/api/triage/{log_id}` | Get a result and all four intake sections |
| `GET` | `/api/triage/history` | List saved records |
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
    "spo2": 98
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
  "onerilen_poliklinik": "Emergency Medicine",
  "aciklama": "No urgent risk was identified by the rules-based assessment.",
  "karar_kaynagi": "KURAL",
  "kodlar": {
    "demografi_id": 12,
    "tibbi_gecmis_id": 12,
    "vitaller_id": 12,
    "sikayet_id": 12
  }
}
```

### Understanding the scores

- `risk_skoru` follows the ESI direction: **1 is most urgent**, **5 is least urgent**.
- `aciliyet_seviyesi` is the reversed project scale shown in the UI: **1 is least urgent**, **5 is most urgent**.
- Color-coded statuses are `KIRMIZI` (red), `SARI` (yellow), and `YESIL` (green).
- For patients aged 65 or older, the final urgency is increased by one level.
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
  app/db/        SQLAlchemy models and data access
  app/models/    Data models and ML classifiers
  pyproject.toml Python dependency and optional integration definitions
  uv.lock        Locked Python dependency versions
  data/          Model training datasets
  tests/         Backend tests
frontend/        React web app and its Docker/nginx configuration
database/        Db2 initialization schema and setup script
docker-compose.yml
```

## License

The code is distributed under the [MIT License](LICENSE). Dataset source and license information is documented in the [model notes](backend/app/models/README.md).
