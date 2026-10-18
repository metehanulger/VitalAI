# AI-Driven Pre-Triage Application

**Tech Stack:** React (Vite) Frontend + FastAPI Backend + IBM DB2 + IBM watsonx.ai

---

## Executive Summary

This application is an AI-enhanced pre-triage system designed to optimize emergency department workflows and ensure patient safety. It combines a strict clinical rule engine (based on NEWS2 standards) with the analytical capabilities of **IBM watsonx.ai**.

**Core Safety Principle:** The system operates on a fail-safe framework. While the clinical rule engine establishes the baseline urgency, `watsonx.ai` analyzes the data for hidden risk factors. Crucially, the AI can **only escalate** the triage priority (e.g., from Yellow to Red) if it detects high-risk patterns; it is restricted from downgrading a critical status flagged by the vitals. All patient records and triage decisions are securely logged in **IBM DB2** using single-transaction operations to ensure data integrity.

---

## Architecture & Data Flow

```text
Triage Interface (4 Modules) ──POST /api/triage──▶  Backend
                                               ├─ Rule Engine (NEWS2 + Critical Thresholds + Keywords)
                                               ├─ IBM watsonx.ai (Optional; can ONLY ESCALATE urgency)
                                               └─ IBM DB2: Single Transaction Logging
                                                  PATIENT_DEMOGRAPHICS ─┐
                                                  MEDICAL_HISTORY      ─┤ IDs ─▶ HOSPITAL_LOG
                                                  REALTIME_VITALS      ─┤        (+ patient status, date,
                                                  COMPLAINT            ─┘           time, queue number)
Results Dashboard  ◀── {log_id, queue_no, patient_status, explanation, codes, ...}
```

---

## Database & UI Modules

| Database Table   | UI Module (Card)        | Fields / Data Collected |
|------------------|-------------------------|-------------------------|
| `HASTA_DEMOGRAFI` | 1. Basic Demographics   | Name, age, height, weight, blood type, ID type (National ID/Passport), ID number |
| `TIBBI_GECMIS`    | 2. Medical History      | Chronic illnesses, regular medications |
| `ANLIK_VITALLER`  | 3. Real-Time Vitals     | Pulse, blood pressure (systolic/diastolic), respiration rate, temperature, SpO2 |
| `SIKAYET`         | 4. Chief Complaint      | Main complaint, pain scale (1-10) |
| `HASTANE_LOG`     | — (System Log)          | IDs of the 4 cards, patient status (RED/YELLOW/GREEN), reasoning/explanation, decision source, date, time, daily queue number |

The database schema can be found at `database/init.sql`. The queue number resets to 1 daily.

---

## Data Dictionary (What Data We Collect & Process)

Table and field names are kept in Turkish to map 1:1 with the backend data models. The English meaning of every name is given below, so the data model can be understood without knowing Turkish.

### Table name translations

| Table (Turkish)   | English Meaning       | Purpose |
|-------------------|-----------------------|---------|
| `HASTA_DEMOGRAFI` | Patient Demographics  | Who the patient is (identity and body measurements). |
| `TIBBI_GECMIS`    | Medical History       | Long-term conditions and regular medication. |
| `ANLIK_VITALLER`  | Real-Time Vitals      | Vital signs measured at the moment of arrival. |
| `SIKAYET`         | Complaint             | Why the patient came to the emergency department. |
| `HASTANE_LOG`     | Hospital Log          | The triage result; links the four tables above together. |

### 1. `HASTA_DEMOGRAFI` — Patient Demographics

| Field        | English Meaning   | Data Type | Example         | Description |
|--------------|-------------------|-----------|-----------------|-------------|
| `isim`       | Full name         | Text      | `Ayşe Yılmaz`   | Patient's first and last name. |
| `yas`        | Age               | Integer   | `34`            | Patient's age in years. |
| `boy`        | Height            | Number    | `165`           | Height in cm. Optional. |
| `kilo`       | Weight            | Decimal   | `60.5`          | Weight in kg. Optional. |
| `kan_grubu`  | Blood type        | Text      | `A+`            | ABO/Rh blood group. Defaults to `BILINMIYOR` (Unknown) if left empty. |
| `kimlik_turu`| ID type           | Text      | `TC`            | Type of identity document: Turkish National ID (`TC`) or Passport. |
| `kimlik_no`  | ID number         | Text      | `10000000146`   | National ID number (checksum-validated) or passport number (5-20 alphanumeric characters). Masked when records are read back through the API. |

### 2. `TIBBI_GECMIS` — Medical History

| Field                | English Meaning        | Data Type | Example  | Description |
|----------------------|------------------------|-----------|----------|-------------|
| `kronik_rahatsizlik` | Chronic illnesses      | Text      | `Asthma` | Long-term conditions the patient already has. |
| `surekli_ilac`       | Regular medications    | Text      | `""`     | Medicines the patient takes on a regular basis. Can be empty. |

### 3. `ANLIK_VITALLER` — Real-Time Vitals

| Field                | English Meaning               | Data Type | Example | Unit / Allowed Range |
|----------------------|-------------------------------|-----------|---------|----------------------|
| `nabiz`              | Pulse (heart rate)            | Integer   | `78`    | beats/min, 20-300 |
| `tansiyon_sistolik`  | Systolic blood pressure       | Integer   | `120`   | mmHg, must be greater than diastolic |
| `tansiyon_diastolik` | Diastolic blood pressure      | Integer   | `80`    | mmHg, must be lower than systolic |
| `solunum`            | Respiration rate              | Integer   | `16`    | breaths/min, 4-80 |
| `ates`               | Body temperature              | Decimal   | `36.8`  | °C, 25-45 |
| `spo2`               | Blood oxygen saturation (SpO2)| Integer   | `98`    | %, 30-100 |

These values feed the NEWS2 (National Early Warning Score 2) rule engine, which calculates the baseline urgency.

### 4. `SIKAYET` — Complaint

| Field          | English Meaning  | Data Type | Example              | Description |
|----------------|------------------|-----------|----------------------|-------------|
| `ana_sikayet`  | Chief complaint  | Text      | `Severe sore throat` | The patient's main reason for visiting, in free text. Scanned for critical keywords by the rule engine and analyzed by watsonx.ai. |
| `agri_skalasi` | Pain scale       | Integer   | `3`                  | Self-reported pain level, 1 (mild) to 10 (worst possible). |

### 5. `HASTANE_LOG` — Hospital Log (Triage Result)

| Field                | English Meaning             | Data Type | Example                  | Description |
|----------------------|-----------------------------|-----------|--------------------------|-------------|
| `log_id`             | Log ID                      | Integer   | `12`                     | Unique ID of the triage record. |
| `sira_no`            | Queue number                | Integer   | `7`                      | Patient's position number for the day. Resets to 1 every day. |
| `tarih`              | Date                        | Date      | `2026-10-17`             | Date of the triage assessment. |
| `saat`               | Time                        | Time      | `15:42:10`               | Time of the triage assessment. |
| `hasta_durumu`       | Patient status              | Text      | `YESIL`                  | Triage priority: `KIRMIZI` (Red, most urgent), `SARI` (Yellow, urgent), `YESIL` (Green, non-urgent). |
| `aciklama`           | Explanation                 | Text      | `No critical findings…`  | Reasoning behind the decision, shown to medical staff. |
| `karar_kaynagi`      | Decision source             | Text      | `KURAL`                  | Who made the decision: `KURAL` (rule engine), `WATSONX`, `KURAL+WATSONX`, or `MANUEL` (manual override by staff). |
| `demografi_id`       | Demographics record ID      | Integer   | `12`                     | Reference to `HASTA_DEMOGRAFI`. |
| `tibbi_gecmis_id`    | Medical history record ID   | Integer   | `12`                     | Reference to `TIBBI_GECMIS`. |
| `vitaller_id`        | Vitals record ID            | Integer   | `12`                     | Reference to `ANLIK_VITALLER`. |
| `sikayet_id`         | Complaint record ID         | Integer   | `12`                     | Reference to `SIKAYET`. |

### Triage status translations

| Value (Turkish) | English | Meaning |
|-----------------|---------|---------|
| `KIRMIZI`       | RED     | Critical, needs immediate attention. |
| `SARI`          | YELLOW  | Urgent, needs prompt attention. |
| `YESIL`         | GREEN   | Non-urgent, can wait. |

---

## Installation & Setup

### 1. Production Environment (IBM DB2 + Backend via Docker)

```bash
# Configure watsonx API keys (optional but recommended for full AI capability)
cp backend/.env.example backend/.env

# Build and start the containers
docker compose up --build
```

> **Note:** During the first initialization, the IBM DB2 setup takes approximately 5-10 minutes. The backend application starts automatically once the DB2 tables are fully provisioned.

- **API Base URL:** http://localhost:8000
- **Swagger UI / Interactive Docs:** http://localhost:8000/docs

### 2. Local Development Environment (Without DB2, via SQLite)

For rapid UI/UX and backend testing without the DB2 overhead, you can run the backend locally using SQLite:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # On macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

**Running Tests:** Execute `pytest` within the `backend` directory.

### Fail-Safe Mechanism

- If the watsonx keys are left empty in the `.env` file, the backend falls back to the rule-based triage system.
- If watsonx latency exceeds the `WATSONX_TIMEOUT` threshold, the system immediately defaults to the rule engine's decision to prevent delays in patient care.

---

## API Reference (For Frontend Integration)

Frontend `.env` configuration:

```env
VITE_API_URL=http://localhost:8000
```

| Method  | Endpoint                                   | Description |
|---------|--------------------------------------------|-------------|
| `POST`  | `/api/triage`                              | Submits the 4 modules of patient data; returns the triage assessment (`201`). |
| `GET`   | `/api/triage?tarih=YYYY-MM-DD&durum=KIRMIZI` | Fetches the daily waiting list, ordered by priority: RED → YELLOW → GREEN. |
| `GET`   | `/api/triage/{log_id}`                     | Retrieves the full hospital log + the 4 data cards (ID numbers are masked for privacy). |
| `PATCH` | `/api/triage/{log_id}`                     | Allows medical staff to manually override the triage status: `{"hasta_durumu": "SARI", "aciklama": "..."}` |
| `GET`   | `/api/triage/secenekler`                   | Retrieves dropdown options: blood types, ID types, and triage statuses. |
| `GET`   | `/api/health`                              | System health check returning the status of the DB2 connection and watsonx availability: `{"durum", "veritabani", "watsonx"}`. |

### Example `POST /api/triage` Payload

> JSON keys are kept in Turkish to ensure 1:1 mapping with the backend data models.

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

### Data Validation Rules

- `boy` (height) and `kilo` (weight) are optional.
- If `kan_grubu` (blood type) is empty, it defaults to `BILINMIYOR` (Unknown). `O+` input is automatically normalized to `0+`.
- Turkish National ID (`TC`) is validated via the official checksum algorithm; passports must be 5-20 alphanumeric characters.
- **Strict vitals boundaries:**
  - Pulse: 20-300
  - Blood pressure: systolic > diastolic
  - Respiration: 4-80
  - Temperature: 25-45 °C
  - SpO2: 30-100 %
  - Pain scale: 1-10

### Example Response (`201 Created`)

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

### Decision Source (`karar_kaynagi`) Indicators

| Value             | Meaning |
|-------------------|---------|
| `KURAL`           | Decision made entirely by the Rule Engine. |
| `WATSONX`         | watsonx escalated the priority based on its analysis. |
| `KURAL+WATSONX`   | Both the Rule Engine and watsonx agreed on the urgency level. |
| `MANUEL`          | A medical professional manually overrode the system's decision. |

---

## Error Handling

| Code  | Meaning |
|-------|---------|
| `422 Unprocessable Entity` | Form validation error. The response includes a `detail[].loc` array pointing to the failing field (e.g., `["body", "vitaller", "spo2"]`). |
| `404 Not Found` | Requested log ID does not exist. |
| `503 Service Unavailable` | The database (DB2) cannot be reached. |
