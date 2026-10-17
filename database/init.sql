-- =====================================================================
-- IBM Z Datathon - VitialAI Acil Servis Ön Triaj Veritabanı Şeması (IBM DB2 & SQL)
-- 4 Kart Tablosu + 1 Hastane Log Tablosu (Master Karar ve Takip)
-- =====================================================================

-- -----------------------------------------------------
-- KART 1: TEMEL DEMOGRAFİ
-- İsim, Yaş, Boy, Kilo, Kan Grubu, Kimlik Türü, Kimlik No
-- -----------------------------------------------------
CREATE TABLE HASTA_DEMOGRAFI (
    ID           INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
    ISIM         VARCHAR(400) NOT NULL,
    YAS          SMALLINT NOT NULL,
    BOY          SMALLINT,
    KILO         DECIMAL(5, 1),
    KAN_GRUBU    VARCHAR(10) NOT NULL DEFAULT 'BILINMIYOR',
    KIMLIK_TURU  VARCHAR(10) NOT NULL,
    KIMLIK_NO    VARCHAR(64) NOT NULL,
    CREATED_AT   TIMESTAMP DEFAULT CURRENT TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT CK_DEMOGRAFI_YAS CHECK (YAS BETWEEN 0 AND 130),
    CONSTRAINT CK_DEMOGRAFI_BOY CHECK (BOY IS NULL OR BOY BETWEEN 20 AND 260),
    CONSTRAINT CK_DEMOGRAFI_KILO CHECK (KILO IS NULL OR KILO BETWEEN 0.5 AND 400),
    CONSTRAINT CK_DEMOGRAFI_KAN CHECK (KAN_GRUBU IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', '0+', '0-', 'BILINMIYOR')),
    CONSTRAINT CK_DEMOGRAFI_KIMLIK CHECK (KIMLIK_TURU IN ('TC', 'PASAPORT'))
);

CREATE INDEX IX_DEMOGRAFI_KIMLIK ON HASTA_DEMOGRAFI(KIMLIK_NO);

-- -----------------------------------------------------
-- KART 2: TIBBİ GEÇMİŞ
-- Kronik Rahatsızlık, Sürekli İlaç
-- -----------------------------------------------------
CREATE TABLE TIBBI_GECMIS (
    ID                 INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
    KRONIK_RAHATSIZLIK VARCHAR(2000),
    SUREKLI_ILAC       VARCHAR(2000),
    CREATED_AT         TIMESTAMP DEFAULT CURRENT TIMESTAMP,
    PRIMARY KEY (ID)
);

-- -----------------------------------------------------
-- KART 3: ANLIK VİTALLER
-- Nabız, Tansiyon (Sistolik / Diyastolik), Solunum, Ateş, SpO2, Troponin
-- -----------------------------------------------------
CREATE TABLE ANLIK_VITALLER (
    ID                 INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
    NABIZ              SMALLINT NOT NULL,
    TANSIYON_SISTOLIK  SMALLINT NOT NULL,
    TANSIYON_DIYASTOLIK SMALLINT NOT NULL,
    SOLUNUM            SMALLINT NOT NULL DEFAULT 16,
    ATES               DECIMAL(4, 1) NOT NULL DEFAULT 36.8,
    SPO2               SMALLINT NOT NULL,
    TROPONIN           DECIMAL(6, 3),
    CREATED_AT         TIMESTAMP DEFAULT CURRENT TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT CK_VITALLER_NABIZ CHECK (NABIZ BETWEEN 20 AND 260),
    CONSTRAINT CK_VITALLER_SISTOLIK CHECK (TANSIYON_SISTOLIK BETWEEN 40 AND 300),
    CONSTRAINT CK_VITALLER_DIYASTOLIK CHECK (TANSIYON_DIYASTOLIK BETWEEN 20 AND 200),
    CONSTRAINT CK_VITALLER_SOLUNUM CHECK (SOLUNUM BETWEEN 4 AND 60),
    CONSTRAINT CK_VITALLER_ATES CHECK (ATES BETWEEN 30.0 AND 45.0),
    CONSTRAINT CK_VITALLER_SPO2 CHECK (SPO2 BETWEEN 40 AND 100)
);

-- -----------------------------------------------------
-- KART 4: HASTA ŞİKAYETİ
-- Ana Şikayet (Metin), Ağrı Skalası (1-10)
-- -----------------------------------------------------
CREATE TABLE HASTA_SIKAYET (
    ID           INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
    ANA_SIKAYET  VARCHAR(4000) NOT NULL,
    AGRI_SKALASI SMALLINT NOT NULL,
    CREATED_AT   TIMESTAMP DEFAULT CURRENT TIMESTAMP,
    PRIMARY KEY (ID),
    CONSTRAINT CK_SIKAYET_AGRI CHECK (AGRI_SKALASI BETWEEN 1 AND 10)
);

-- -----------------------------------------------------
-- TABLO 5: HASTANE LOG (Master Karar ve Takip Tablosu)
-- 4 kart kaydedildiğinde her birinin ID'sini ve AI kararını tutar
-- -----------------------------------------------------
CREATE TABLE HASTANE_LOG (
    ID                          INTEGER NOT NULL GENERATED ALWAYS AS IDENTITY (START WITH 1 INCREMENT BY 1),
    SIRA_NO                     INTEGER NOT NULL,
    TARIH                       DATE NOT NULL,
    SAAT                        TIME NOT NULL,
    
    -- 4 Kartın Referans Kodları (Foreign Keys)
    DEMOGRAFI_ID                INTEGER NOT NULL,
    TIBBI_GECMIS_ID             INTEGER NOT NULL,
    VITALLER_ID                 INTEGER NOT NULL,
    SIKAYET_ID                  INTEGER NOT NULL,
    
    -- Triaj ve Yapay Zekâ Çıktıları
    DURUM                       VARCHAR(20) NOT NULL, -- KIRMIZI, SARI, YESIL
    RISK_SKORU                  SMALLINT NOT NULL,    -- ESI Seviyesi 1-5
    ONERILEN_POLIKLINIK         VARCHAR(150),         -- Kardiyoloji, Nöroloji vb.
    BIRIM_UYUMLULUK_JSON        VARCHAR(4000),        -- Sıralı birim listesi ve skorları
    KRITIK_BULGU                VARCHAR(1500),        -- Kararı belirleyen kritik bulgu
    ERKEN_UYARI_NOTU            VARCHAR(1500),        -- Acil hekimi için erken uyarı
    ACIKLAMA                    VARCHAR(2000),        -- Klinik gerekçe özeti
    KARAR_KAYNAGI               VARCHAR(50) NOT NULL, -- WATSONX, GEMINI, KURAL, KURAL+AI
    NEWS2_SKORU                 SMALLINT DEFAULT 0,
    
    ISLENDI                     SMALLINT NOT NULL DEFAULT 0,
    CREATED_AT                  TIMESTAMP DEFAULT CURRENT TIMESTAMP,
    
    PRIMARY KEY (ID),
    CONSTRAINT UQ_LOG_TARIH_SIRA UNIQUE (TARIH, SIRA_NO),
    CONSTRAINT FK_LOG_DEMOGRAFI FOREIGN KEY (DEMOGRAFI_ID) REFERENCES HASTA_DEMOGRAFI(ID) ON DELETE CASCADE,
    CONSTRAINT FK_LOG_GECMIS FOREIGN KEY (TIBBI_GECMIS_ID) REFERENCES TIBBI_GECMIS(ID) ON DELETE CASCADE,
    CONSTRAINT FK_LOG_VITALLER FOREIGN KEY (VITALLER_ID) REFERENCES ANLIK_VITALLER(ID) ON DELETE CASCADE,
    CONSTRAINT FK_LOG_SIKAYET FOREIGN KEY (SIKAYET_ID) REFERENCES HASTA_SIKAYET(ID) ON DELETE CASCADE,
    CONSTRAINT CK_LOG_DURUM CHECK (DURUM IN ('KIRMIZI', 'SARI', 'YESIL'))
);

CREATE INDEX IX_LOG_TARIH_DURUM ON HASTANE_LOG(TARIH, DURUM, SIRA_NO);
CREATE INDEX IX_LOG_CREATED_AT ON HASTANE_LOG(CREATED_AT DESC);
