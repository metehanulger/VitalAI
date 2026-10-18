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

## Data Collected

Table and field names are in Turkish (1:1 with the backend models). English meanings are given below. Schema: `database/init.sql`.

| Table (UI Module) | English Name | Fields (English meaning) |
|---|---|---|
| `HASTA_DEMOGRAFI` (1. Basic Demographics) | Patient Demographics | `isim` name, `yas` age, `boy` height (cm, optional), `kilo` weight (kg, optional), `kan_grubu` blood type, `kimlik_turu` ID type (National ID / Passport), `kimlik_no` ID number |
| `TIBBI_GECMIS` (2. Medical History) | Medical History | `kronik_rahatsizlik` chronic illnesses, `surekli_ilac` regular medications |
| `ANLIK_VITALLER` (3. Real-Time Vitals) | Real-Time Vitals | `nabiz` pulse, `tansiyon_sistolik` / `tansiyon_diastolik` blood pressure, `solunum` respiration rate, `ates` temperature, `spo2` oxygen saturation |
| `SIKAYET` (4. Chief Complaint) | Complaint | `ana_sikayet` main complaint (free text), `agri_skalasi` pain scale (1-10) |
| `HASTANE_LOG` (system log) | Hospital Log | IDs of the 4 records, `hasta_durumu` status, `aciklama` explanation, `karar_kaynagi` decision source, `tarih` date, `saat` time, `sira_no` daily queue number (resets to 1 each day) |

**Status values:** `KIRMIZI` = RED (critical), `SARI` = YELLOW (urgent), `YESIL` = GREEN (non-urgent).
**Decision source:** `KURAL` = rule engine, `WATSONX` = AI escalated, `KURAL+WATSONX` = both agree, `MANUEL` = manual override by staff.

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

### Validation Rules

- `boy` and `kilo` are optional. Empty `kan_grubu` defaults to `BILINMIYOR` (Unknown). `O+` is normalized to `0+`.
- Turkish National ID is checksum-validated; passports must be 5-20 alphanumeric characters.
- Vitals limits: pulse 20-300, systolic > diastolic, respiration 4-80, temperature 25-45 °C, SpO2 30-100 %, pain scale 1-10.

### Errors

| Code | Meaning |
|---|---|
| `422` | Validation error; `detail[].loc` points to the failing field (e.g., `["body", "vitaller", "spo2"]`). |
| `404` | Log ID not found. |
| `503` | Database (DB2) unreachable. |
