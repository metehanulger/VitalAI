CREATE TABLE IF NOT EXISTS HASTA_DEMOGRAFI (
    ID           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ISIM         VARCHAR(400) NOT NULL,
    YAS          SMALLINT NOT NULL,
    BOY          SMALLINT,
    KILO         DECIMAL(5, 1),
    KAN_GRUBU    VARCHAR(10) NOT NULL DEFAULT 'BILINMIYOR',
    KIMLIK_TURU  VARCHAR(10) NOT NULL DEFAULT 'TC',
    KIMLIK_NO    VARCHAR(64) NOT NULL,
    CREATED_AT   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT CK_DEMO_YAS CHECK (YAS BETWEEN 0 AND 130),
    CONSTRAINT CK_DEMO_BOY CHECK (BOY IS NULL OR BOY BETWEEN 20 AND 260),
    CONSTRAINT CK_DEMO_KILO CHECK (KILO IS NULL OR KILO BETWEEN 0.5 AND 400)
);

CREATE INDEX IF NOT EXISTS IX_DEMO_KIMLIK ON HASTA_DEMOGRAFI(KIMLIK_NO);
CREATE TABLE IF NOT EXISTS TIBBI_GECMIS (
    ID                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    KRONIK_RAHATSIZLIK VARCHAR(2000),
    SUREKLI_ILAC       VARCHAR(2000),
    CREATED_AT         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ANLIK_VITALLER (
    ID                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    NABIZ              SMALLINT NOT NULL,
    TANSIYON_SISTOLIK  SMALLINT NOT NULL,
    TANSIYON_DIYASTOLIK SMALLINT NOT NULL,
    SOLUNUM            SMALLINT NOT NULL DEFAULT 16,
    ATES               DECIMAL(4, 1) NOT NULL DEFAULT 36.8,
    SPO2               SMALLINT NOT NULL,
    TROPONIN           DECIMAL(6, 3),
    CREATED_AT         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT CK_VIT_NABIZ CHECK (NABIZ BETWEEN 20 AND 260),
    CONSTRAINT CK_VIT_SPO2 CHECK (SPO2 BETWEEN 40 AND 100)
);
CREATE TABLE IF NOT EXISTS HASTA_SIKAYET (
    ID           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ANA_SIKAYET  VARCHAR(4000) NOT NULL,
    AGRI_SKALASI SMALLINT NOT NULL DEFAULT 1,
    CREATED_AT   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT CK_SIKAYET_AGRI CHECK (AGRI_SKALASI BETWEEN 1 AND 10)
);
CREATE TABLE IF NOT EXISTS HASTANE_LOG (
    ID                          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    SIRA_NO                     INTEGER NOT NULL,
    TARIH                       DATE NOT NULL,
    SAAT                        TIME NOT NULL,
    DEMOGRAFI_ID                INTEGER NOT NULL REFERENCES HASTA_DEMOGRAFI(ID) ON DELETE CASCADE,
    TIBBI_GECMIS_ID             INTEGER NOT NULL REFERENCES TIBBI_GECMIS(ID) ON DELETE CASCADE,
    VITALLER_ID                 INTEGER NOT NULL REFERENCES ANLIK_VITALLER(ID) ON DELETE CASCADE,
    SIKAYET_ID                  INTEGER NOT NULL REFERENCES HASTA_SIKAYET(ID) ON DELETE CASCADE,
    DURUM                       VARCHAR(20) NOT NULL,
    RISK_SKORU                  SMALLINT NOT NULL,
    ONERILEN_POLIKLINIK         VARCHAR(150),
    BIRIM_UYUMLULUK_JSON        VARCHAR(4000),
    KRITIK_BULGU                VARCHAR(1500),
    ERKEN_UYARI_NOTU            VARCHAR(1500),
    ACIKLAMA                    VARCHAR(2000),
    KARAR_KAYNAGI               VARCHAR(50) NOT NULL DEFAULT 'LLM',
    NEWS2_SKORU                 SMALLINT DEFAULT 0,

    ISLENDI                     SMALLINT NOT NULL DEFAULT 0,
    CREATED_AT                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT UQ_LOG_TARIH_SIRA UNIQUE (TARIH, SIRA_NO)
);

CREATE INDEX IF NOT EXISTS IX_LOG_TARIH_DURUM ON HASTANE_LOG(TARIH, DURUM, SIRA_NO);
CREATE INDEX IF NOT EXISTS IX_LOG_CREATED_AT ON HASTANE_LOG(CREATED_AT DESC);
CREATE TABLE IF NOT EXISTS HASTALIK_SEVK_REFERANS (
    ID                     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    HASTALIK_ADI           VARCHAR(200) NOT NULL,
    ICD10_KODU             VARCHAR(20),
    SEMPTOMLAR             VARCHAR(2000) NOT NULL,
    BIRINCIL_POLIKLINIK    VARCHAR(100) NOT NULL,
    IKINCIL_POLIKLINIK     VARCHAR(100),
    VARSAYILAN_TRIAJ_KODU  VARCHAR(20) NOT NULL,
    ACIKLAMA               VARCHAR(1000)
);

CREATE INDEX IF NOT EXISTS IX_ML_HASTALIK ON HASTALIK_SEVK_REFERANS(HASTALIK_ADI);
CREATE INDEX IF NOT EXISTS IX_ML_BIRINCIL ON HASTALIK_SEVK_REFERANS(BIRINCIL_POLIKLINIK);
INSERT INTO HASTALIK_SEVK_REFERANS (HASTALIK_ADI, ICD10_KODU, SEMPTOMLAR, BIRINCIL_POLIKLINIK, IKINCIL_POLIKLINIK, VARSAYILAN_TRIAJ_KODU, ACIKLAMA)
VALUES
('Acute myocardial infarction', 'I21.9', 'Crushing chest pain radiating to the left arm, cold sweating, tachycardia, dyspnea, elevated troponin', 'Cardiology', 'Emergency Medicine', 'KIRMIZI', 'Urgent angiography and cardiac intensive care are required.'),
('Acute ischemic stroke', 'I63.9', 'Sudden facial asymmetry, arm weakness, speech difficulty (aphasia), confusion', 'Neurology', 'Interventional Radiology', 'KIRMIZI', 'Thrombolytic treatment within the first 4.5 hours is critical.'),
('Acute pulmonary embolism', 'I26.9', 'Sudden sharp chest pain, marked tachypnea, hemoptysis, low SpO2', 'Pulmonology', 'Cardiology', 'KIRMIZI', 'Urgent CT angiography and oxygen support are required.'),
('Pneumothorax', 'J93.9', 'Severe one-sided chest pain while breathing, reduced breath sounds, cyanosis', 'Thoracic Surgery', 'Emergency Medicine', 'KIRMIZI', 'There is a risk of tension pneumothorax; urgent decompression is required.'),
('Acute appendicitis', 'K35.8', 'Pain starting around the navel and moving to the right lower abdomen, nausea, vomiting, leukocytosis', 'General Surgery', 'Gastroenterology', 'SARI', 'Surgery may be required; urgent ultrasound or CT is recommended.'),
('Acute cholecystitis', 'K81.0', 'Severe cramping pain in the right upper abdomen radiating to the back, worsening after meals, fever', 'General Surgery', 'Gastroenterology', 'SARI', 'Assess for biliary colic and risk of perforation.'),
('Urinary stone / renal colic', 'N20.1', 'Severe flank pain radiating to the groin, hematuria (blood in urine)', 'Urology', 'Internal Medicine', 'SARI', 'Urgent analgesia and urinary tract imaging are required.'),
('Pneumonia', 'J18.9', 'High fever, productive cough with dark sputum, side pain, crackles on auscultation', 'Pulmonology', 'Infectious Diseases', 'SARI', 'Antibiotic treatment and a chest X-ray are required.'),
('Diabetic ketoacidosis', 'E10.1', 'Excessive thirst, polyuria, fruity-smelling breath, abdominal pain, blood glucose above 300 mg/dL', 'Endocrinology', 'Internal Medicine', 'KIRMIZI', 'Begin the emergency IV insulin and hydration protocol.'),
('Hypertensive crisis', 'I10', 'Blood pressure above 180/120 mmHg, severe headache, blurred vision, nosebleed', 'Cardiology', 'Internal Medicine', 'SARI', 'Assess for end-organ damage involving the heart, brain, or kidneys.'),
('Open fracture / joint dislocation', 'T14.2', 'Abnormal limb movement, open wound, bone fragment, severe pain, deformity', 'Orthopedics and Traumatology', 'Emergency Medicine', 'SARI', 'Urgent reduction, splinting, and infection prophylaxis may be required.'),
('Acute meningitis', 'G03.9', 'Neck stiffness, high fever, photophobia, petechial rash', 'Infectious Diseases', 'Neurology', 'KIRMIZI', 'Urgent lumbar puncture and empiric antibiotics are required.'),
('Gastrointestinal bleeding', 'K92.2', 'Melena (black tarry stool), hematemesis (coffee-ground vomit), dizziness, anemia', 'Gastroenterology', 'General Surgery', 'KIRMIZI', 'Prepare for urgent endoscopy and blood transfusion.'),
('Acute sinusitis / upper respiratory infection', 'J01.9', 'Facial pressure, nasal congestion, mild headache, throat irritation', 'Otolaryngology', 'Internal Medicine', 'YESIL', 'Outpatient medical treatment and rest are sufficient.'),
('Minor soft-tissue injury', 'T14.0', 'Mild sprain, localized swelling, minimal pain with movement, normal circulation and sensation', 'Orthopedics and Traumatology', 'Emergency Medicine', 'YESIL', 'Cold application, elevation, and a simple analgesic are sufficient.');
