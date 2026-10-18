AI-Driven Pre-Triage ApplicationTech Stack: React (Vite) Frontend + FastAPI Backend + IBM DB2 + IBM watsonx.aiExecutive SummaryThis application is an AI-enhanced pre-triage system designed to optimize emergency department workflows and ensure patient safety. It combines a strict clinical rule engine (based on NEWS2 standards) with the advanced analytical capabilities of IBM watsonx.ai.Core Safety Principle: The system operates on a fail-safe framework. While the clinical rule engine establishes the baseline urgency, watsonx.ai analyzes the data for hidden risk factors. Crucially, the AI can only escalate the triage priority (e.g., from Yellow to Red) if it detects high-risk patterns; it is mathematically restricted from downgrading a critical status flagged by the vitals. All patient records and triage decisions are securely logged in IBM DB2 using single-transaction operations to ensure data integrity.Architecture & Data FlowPlaintextTriage Interface (4 Modules) ──POST /api/triage──▶  Backend
                                               ├─ Rule Engine (NEWS2 + Critical Thresholds + Keywords)
                                               ├─ IBM watsonx.ai (Optional; can ONLY ESCALATE urgency)
                                               └─ IBM DB2: Single Transaction Logging
                                                  PATIENT_DEMOGRAPHICS ─┐
                                                  MEDICAL_HISTORY      ─┤ IDs ─▶ HOSPITAL_LOG
                                                  REALTIME_VITALS      ─┤        (+ patient status, date,
                                                  COMPLAINT            ─┘           time, queue number)
Results Dashboard  ◀── {log_id, queue_no, patient_status, explanation, codes, ...}
Database TableUI Module (Card)Fields / Data CollectedHASTA_DEMOGRAFI1. Basic DemographicsName, age, height, weight, blood type, ID type (National ID/Passport), ID numberTIBBI_GECMIS2. Medical HistoryChronic illnesses, regular medicationsANLIK_VITALLER3. Real-Time VitalsPulse, blood pressure (systolic/diastolic), respiration rate, temperature, SpO2SIKAYET4. Chief ComplaintMain complaint, pain scale (1-10)HASTANE_LOG— (System Log)IDs of the 4 cards, patient status (RED/YELLOW/GREEN), reasoning/explanation, decision source, date, time, daily queue numberDatabase schema source can be found at database/init.sql. The queue number resets to 1 daily.Installation & Setup1. Production Environment (IBM DB2 + Backend via Docker)Bash# Configure watsonx API keys (optional but recommended for full AI capability)
cp backend/.env.example backend/.env  

# Build and start the containers
docker compose up --build
Note: During the first initialization, the IBM DB2 setup takes approximately 5-10 minutes. The backend application will automatically start once the DB2 tables are fully provisioned.API Base URL: http://localhost:8000Swagger UI / Interactive Docs: http://localhost:8000/docs2. Local Development Environment (Without DB2, via SQLite)For rapid UI/UX and backend testing without the DB2 overhead, you can run the backend locally using SQLite:Bashcd backend
python -m venv .venv
.venv\Scripts\activate            # On macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
Running Tests: Execute pytest within the backend directory.Fail-Safe Mechanism: If the watsonx keys are left empty in the .env file, the backend will seamlessly fall back to the rule-based triage system. If watsonx experiences latency exceeding the WATSONX_TIMEOUT threshold, the system immediately defaults to the rule engine's decision to prevent delays in patient care.API Reference (For Frontend Integration)Frontend .env configuration: VITE_API_URL=http://localhost:8000MethodEndpointDescriptionPOST/api/triageSubmits the 4 modules of patient data; returns the triage assessment (201).GET/api/triage?tarih=YYYY-MM-DD&durum=KIRMIZIFetches the daily waiting list, ordered by priority: RED -> YELLOW -> GREEN.GET/api/triage/{log_id}Retrieves the full hospital log + the 4 data cards (ID numbers are masked for privacy).PATCH/api/triage/{log_id}Allows medical staff to manually override the triage status: {"hasta_durumu": "SARI", "aciklama": "..."}GET/api/triage/seceneklerRetrieves dropdown options: blood types, ID types, and triage statuses.GET/api/healthSystem health check returning status of the DB2 connection and WatsonX availability: {"durum", "veritabani", "watsonx"}.Example POST /api/triage Payload(Note: JSON keys are kept in Turkish to ensure 1:1 mapping with the backend data models.)JSON{
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
Data Validation Rules:boy (height) and kilo (weight) are optional. If kan_grubu (blood type) is empty, it defaults to BILINMIYOR (Unknown). O+ input is automatically normalized to 0+.Turkish National ID (TC) is validated via cryptographic algorithm; Passports must be 5-20 alphanumeric characters.Strict Vitals Boundaries: Pulse: 20-300, Systolic > Diastolic, Respiration: 4-80, Temperature: 25-45°C, SpO2: 30-100%, Pain Scale: 1-10.Example Response (201 Created)JSON{
  "log_id": 12, 
  "sira_no": 7, 
  "tarih": "2026-10-17", 
  "saat": "15:42:10",
  "hasta_durumu": "YESIL",
  "aciklama": "No critical findings in rule-based assessment (NEWS2=0).",
  "karar_kaynagi": "KURAL",
  "kodlar": { "demografi_id": 12, "tibbi_gecmis_id": 12, "vitaller_id": 12, "sikayet_id": 12 }
}
karar_kaynagi (Decision Source) Indicators:KURAL: Decision made entirely by the Rule Engine.WATSONX: WatsonX escalated the priority based on its analysis.KURAL+WATSONX: Both the Rule Engine and WatsonX agreed on the urgency level.MANUEL: A medical professional manually overrode the system's decision.Error Handling422 Unprocessable Entity: Form validation error. The response includes a detail[].loc array pointing exactly to the failing field (e.g., ["body", "vitaller", "spo2"]).404 Not Found: Requested log ID does not exist.503 Service Unavailable: The database (DB2) cannot be reached.
