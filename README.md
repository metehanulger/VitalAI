# AI-Driven Pre-Triage Application

**Tech Stack:** React (Vite) + FastAPI + IBM DB2 + IBM watsonx.ai

## Overview

An AI-enhanced pre-triage system for emergency departments. A clinical rule engine (NEWS2) sets the baseline urgency, and **IBM watsonx.ai** looks for hidden risk factors.

**Safety principle:** the AI can only **escalate** priority (e.g., Yellow → Red). It can never downgrade a critical status flagged by the vitals. Every record and decision is logged in IBM DB2 in a single transaction.

## Architecture

```text
Triage Interface (4 Modules) ──POST /api/triage──▶  Backend
                                               ├─ Rule Engine (NEWS2 + Critical Thresholds + Keywords)
                                               ├─ IBM watsonx.ai (Optional; can ONLY ESCALATE urgency)
                                               └─ IBM DB2: Single Transaction Logging
                                                  PATIENT_DEMOGRAPHICS ─┐
                                                  MEDICAL_HISTORY      ─┤ IDs ─▶ HOSPITAL_LOG
                                                  REALTIME_VITALS      ─┤        (+ status, date,
                                                  COMPLAINT            ─┘           time, queue number)
Results Dashboard  ◀── {log_id, sira_no, hasta_durumu, aciklama, kodlar, ...}
```

## Data We Collect

Each triage visit collects four groups of data (one per UI card), stored in four tables, plus one log table that ties them together. Table and field names are in Turkish to map 1:1 with the backend models; the English meaning is given for each. Schema: `database/init.sql`.

### 1. `HASTA_DEMOGRAFI` — Patient Demographics
*Who the patient is.*

| Field | Meaning | Example / Rule |
|---|---|---|
| `isim` | Full name | `Ayşe Yılmaz` |
| `yas` | Age (years) | `34` |
| `boy` | Height in cm (optional) | `165` |
| `kilo` | Weight in kg (optional) | `60.5` |
| `kan_grubu` | Blood type | `A+`; empty → `BILINMIYOR` (Unknown) |
| `kimlik_turu` | ID document type | `TC` (Turkish National ID) or Passport |
| `kimlik_no` | ID number | National ID is checksum-validated; passport is 5-20 alphanumeric characters. Masked in API reads. |

### 2. `TIBBI_GECMIS` — Medical History
*Conditions the patient already has.*

| Field | Meaning | Example / Rule |
|---|---|---|
| `kronik_rahatsizlik` | Chronic illnesses | `Asthma` |
| `surekli_ilac` | Regularly used medications | Can be empty |

### 3. `ANLIK_VITALLER` — Real-Time Vitals
*Vital signs measured on arrival. These feed the NEWS2 score.*

| Field | Meaning | Example / Allowed Range |
|---|---|---|
| `nabiz` | Pulse (beats/min) | `78` (20-300) |
| `tansiyon_sistolik` | Systolic blood pressure (mmHg) | `120` (must be > diastolic) |
| `tansiyon_diastolik` | Diastolic blood pressure (mmHg) | `80` |
| `solunum` | Respiration rate (breaths/min) | `16` (4-80) |
| `ates` | Body temperature (°C) | `36.8` (25-45) |
| `spo2` | Blood oxygen saturation (%) | `98` (30-100) |

### 4. `SIKAYET` — Complaint
*Why the patient came in.*

| Field | Meaning | Example / Rule |
|---|---|---|
| `ana_sikayet` | Chief complaint (free text) | `Severe sore throat`; scanned for critical keywords and analyzed by watsonx.ai |
| `agri_skalasi` | Self-reported pain level | `3` (1 = mild, 10 = worst) |

### 5. `HASTANE_LOG` — Hospital Log (Triage Result)
*The decision, linked to the four records above.*

| Field | Meaning | Example / Rule |
|---|---|---|
| `log_id` | Unique ID of the triage record | `12` |
| `sira_no` | Daily queue number | `7` (resets to 1 every day) |
| `tarih` / `saat` | Date / time of the assessment | `2026-10-17` / `15:42:10` |
| `hasta_durumu` | Patient status (priority) | `KIRMIZI`, `SARI` or `YESIL` (see below) |
| `aciklama` | Explanation of the decision | `No critical findings in rule-based assessment (NEWS2=0).` |
| `karar_kaynagi` | Who made the decision | `KURAL`, `WATSONX`, `KURAL+WATSONX` or `MANUEL` (see below) |
| `demografi_id`, `tibbi_gecmis_id`, `vitaller_id`, `sikayet_id` | References to the four records above | `12` |

**Patient status (`hasta_durumu`)**

| Value | English | Meaning |
|---|---|---|
| `KIRMIZI` | RED | Critical, needs immediate attention |
| `SARI` | YELLOW | Urgent, needs prompt attention |
| `YESIL` | GREEN | Non-urgent, can wait |

**Decision source (`karar_kaynagi`)**

| Value | Meaning |
|---|---|
| `KURAL` | Decided entirely by the rule engine |
| `WATSONX` | watsonx.ai escalated the priority |
| `KURAL+WATSONX` | Rule engine and watsonx.ai agreed |
| `MANUEL` | Manually overridden by medical staff |

## Installation

### Production (IBM DB2 + Backend via Docker)

```bash
cp backend/.env.example backend/.env   # add watsonx keys (optional)
docker compose up --build
```

First DB2 initialization takes about 5-10 minutes; the backend starts automatically afterwards.

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

### Local Development (SQLite, no DB2)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Run tests with `pytest` inside `backend`.

### Fail-Safe Behavior

- Empty watsonx keys → backend falls back to the rule-based system.
- watsonx slower than `WATSONX_TIMEOUT` → the rule engine's decision is used immediately.

## API Reference

Frontend `.env`: `VITE_API_URL=http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/triage` | Submit the 4 modules; returns the triage result (`201`). |
| `GET` | `/api/triage?tarih=YYYY-MM-DD&durum=KIRMIZI` | Daily waiting list, ordered RED → YELLOW → GREEN. |
| `GET` | `/api/triage/{log_id}` | Full log + 4 data cards (ID numbers masked). |
| `PATCH` | `/api/triage/{log_id}` | Manual override: `{"hasta_durumu": "SARI", "aciklama": "..."}` |
| `GET` | `/api/triage/secenekler` | Dropdown options (blood types, ID types, statuses). |
| `GET` | `/api/health` | Health check: `{"durum", "veritabani", "watsonx"}`. |

### Example Request: `POST /api/triage`

```json
{
  "demografi": {
    "isim": "Ayşe Yılmaz", "yas": 34, "boy": 165, "kilo": 60.5,
    "kan_grubu": "A+", "kimlik_turu": "TC", "kimlik_no": "10000000146"
  },
  "tibbi_gecmis": { "kronik_rahatsizlik": "Asthma", "surekli_ilac": "" },
  "vitaller": {
    "nabiz": 78, "tansiyon_sistolik": 120, "tansiyon_diastolik": 80,
    "solunum": 16, "ates": 36.8, "spo2": 98
  },
  "sikayet": { "ana_sikayet": "Severe sore throat", "agri_skalasi": 3 }
}
```

### Example Response: `201 Created`

```json
{
  "log_id": 12,
  "sira_no": 7,
  "tarih": "2026-10-17",
  "saat": "15:42:10",
  "hasta_durumu": "YESIL",
  "aciklama": "No critical findings in rule-based assessment (NEWS2=0).",
  "karar_kaynagi": "KURAL",
  "kodlar": { "demografi_id": 12, "tibbi_gecmis_id": 12, "vitaller_id": 12, "sikayet_id": 12 }
}
```

### Validation Notes

- `O+` blood type input is normalized to `0+`.
- All field rules (ranges, ID checks) are listed in the Data We Collect section above.

### Errors

| Code | Meaning |
|---|---|
| `422` | Validation error; `detail[].loc` points to the failing field (e.g., `["body", "vitaller", "spo2"]`). |
| `404` | Log ID not found. |
| `503` | Database (DB2) unreachable. |
