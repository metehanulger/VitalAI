-- =====================================================================
-- VitialAI - Yüksek Performanslı Acil Servis Ön Triaj ve ML Veritabanı
-- Mimari: PostgreSQL & IBM DB2 Uyumlu Hibrit SQL + JSONB Şeması
-- 
-- 1. Kart 1: HASTA_DEMOGRAFI
-- 2. Kart 2: TIBBI_GECMIS
-- 3. Kart 3: ANLIK_VITALLER
-- 4. Kart 4: HASTA_SIKAYET
-- 5. Master: HASTANE_LOG (4 Kartı bağlayan ve AI kararlarını tutan tablo)
-- 6. ML Veri Seti: HASTALIK_SEVK_REFERANS (Hastalık -> Sevk Polikliniği Eğitimi)
-- =====================================================================

-- -----------------------------------------------------
-- KART 1: TEMEL DEMOGRAFİ
-- -----------------------------------------------------
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

-- -----------------------------------------------------
-- KART 2: TIBBİ GEÇMİŞ
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS TIBBI_GECMIS (
    ID                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    KRONIK_RAHATSIZLIK VARCHAR(2000),
    SUREKLI_ILAC       VARCHAR(2000),
    CREATED_AT         TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------
-- KART 3: ANLIK VİTALLER
-- -----------------------------------------------------
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

-- -----------------------------------------------------
-- KART 4: HASTA ŞİKAYETİ VE AĞRI
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS HASTA_SIKAYET (
    ID           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ANA_SIKAYET  VARCHAR(4000) NOT NULL,
    AGRI_SKALASI SMALLINT NOT NULL DEFAULT 1,
    CREATED_AT   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT CK_SIKAYET_AGRI CHECK (AGRI_SKALASI BETWEEN 1 AND 10)
);

-- -----------------------------------------------------
-- TABLO 5: HASTANE LOG (Master Karar ve Takip Tablosu)
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS HASTANE_LOG (
    ID                          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    SIRA_NO                     INTEGER NOT NULL,
    TARIH                       DATE NOT NULL,
    SAAT                        TIME NOT NULL,
    
    -- 4 Kartın Referans Kodları (Foreign Keys)
    DEMOGRAFI_ID                INTEGER NOT NULL REFERENCES HASTA_DEMOGRAFI(ID) ON DELETE CASCADE,
    TIBBI_GECMIS_ID             INTEGER NOT NULL REFERENCES TIBBI_GECMIS(ID) ON DELETE CASCADE,
    VITALLER_ID                 INTEGER NOT NULL REFERENCES ANLIK_VITALLER(ID) ON DELETE CASCADE,
    SIKAYET_ID                  INTEGER NOT NULL REFERENCES HASTA_SIKAYET(ID) ON DELETE CASCADE,
    
    -- Triaj ve Yapay Zekâ Çıktıları
    DURUM                       VARCHAR(20) NOT NULL, -- KIRMIZI, SARI, YESIL
    RISK_SKORU                  SMALLINT NOT NULL,    -- ESI 1-5
    ONERILEN_POLIKLINIK         VARCHAR(150),
    BIRIM_UYUMLULUK_JSON        VARCHAR(4000),        -- Hibrit JSONB / Text
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

-- =====================================================================
-- TABLO 6: ML EĞİTİM VE SEVK REFERANS VERİ SETİ (HASTALIK -> POLİKLİNİK)
-- Makine öğrenimi modelini eğitmek için hazır klinik eşleştirme tablosu
-- =====================================================================
CREATE TABLE IF NOT EXISTS HASTALIK_SEVK_REFERANS (
    ID                     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    HASTALIK_ADI           VARCHAR(200) NOT NULL,
    ICD10_KODU             VARCHAR(20),
    SEMPTOMLAR             VARCHAR(2000) NOT NULL,
    BIRINCIL_POLIKLINIK    VARCHAR(100) NOT NULL,
    IKINCIL_POLIKLINIK     VARCHAR(100),
    VARSAYILAN_TRIAJ_KODU  VARCHAR(20) NOT NULL, -- KIRMIZI, SARI, YESIL
    ACIKLAMA               VARCHAR(1000)
);

CREATE INDEX IF NOT EXISTS IX_ML_HASTALIK ON HASTALIK_SEVK_REFERANS(HASTALIK_ADI);
CREATE INDEX IF NOT EXISTS IX_ML_BIRINCIL ON HASTALIK_SEVK_REFERANS(BIRINCIL_POLIKLINIK);

-- -----------------------------------------------------
-- ML EĞİTİMİ İÇİN BAŞLANGIÇ KLİNİK VERİ SETİ (SEED DATA)
-- -----------------------------------------------------
INSERT INTO HASTALIK_SEVK_REFERANS (HASTALIK_ADI, ICD10_KODU, SEMPTOMLAR, BIRINCIL_POLIKLINIK, IKINCIL_POLIKLINIK, VARSAYILAN_TRIAJ_KODU, ACIKLAMA)
VALUES
('Akut Miyokard Enfarktüsü (Kalp Krizi)', 'I21.9', 'Sol kola vuran ezici göğüs ağrısı, soğuk terleme, taşikardi, dispne, troponin yüksekliği', 'Kardiyoloji', 'Acil Tıp', 'KIRMIZI', 'Acil anjiyografi ve kardiyak yoğun bakım gerektirir.'),
('Akut İskemik İnme (Felç)', 'I63.9', 'Ani yüz asimetrisi, kolda güç kaybı, konuşma bozukluğu (afazi), bilinç bulanıklığı', 'Nöroloji', 'Girişimsel Radyoloji', 'KIRMIZI', 'İlk 4.5 saatte trombolitik tedavi hayati önemdedir.'),
('Akut Pulmoner Emboli', 'I26.9', 'Ani başlayan batıcı göğüs ağrısı, derin taşipne, hemoptizi, SpO2 düşüklüğü', 'Göğüs Hastalıkları', 'Kardiyoloji', 'KIRMIZI', 'Acil BT anjiyo ve oksijen desteği gerekir.'),
('Pnömotoraks (Akciğer Sönmesi)', 'J93.9', 'Nefes alırken tek taraflı şiddetli göğüs batması, solunum seslerinde azalma, siyanoz', 'Göğüs Cerrahisi', 'Acil Tıp', 'KIRMIZI', 'Tansiyon pnömotoraks riski; acil dekompresyon gerekir.'),
('Akut Apandisit', 'K35.8', 'Göbek çevresinde başlayıp sağ alt kadrana yerleşen ağrı, bulantı, kusma, lökositoz', 'Genel Cerrahi', 'Gastroenteroloji', 'SARI', 'Cerrahi operasyon gerekebilir; acil ultrason/BT önerilir.'),
('Akut Kolesistit (Safra Kesesi İltihabı)', 'K81.0', 'Sağ üst kadranda sırta vuran şiddetli kramp tarzı ağrı, yemek sonrası kötüleşme, ateş', 'Genel Cerrahi', 'Gastroenteroloji', 'SARI', 'Biliyer kolik ve perforasyon riski değerlendirilmelidir.'),
('Üriner Taş / Renal Kolik', 'N20.1', 'Böğür bölgesinde (yanlarda) kasığa vuran kıvrandırıcı ağrı, hematüri (idrarda kan)', 'Üroloji', 'Genel Dahiliye', 'SARI', 'Acil analjezik ve üriner sistem görüntülemesi gerekir.'),
('Pnömoni (Zatürre)', 'J18.9', 'Yüksek ateş, prodüktif öksürük (koyu balgam), yan ağrısı, oskültasyonda raller', 'Göğüs Hastalıkları', 'Enfeksiyon Hastalıkları', 'SARI', 'Antibiyoterapi ve akciğer grafisi gerekir.'),
('Diyabetik Ketoasidoz', 'E10.1', 'Aşırı susama, poliüri, aseton kokulu nefes, karın ağrısı, kan şekeri > 300 mg/dL', 'Endokrinoloji', 'Genel Dahiliye', 'KIRMIZI', 'Acil IV insülin ve hidrasyon protokolü başlatılmalıdır.'),
('Hipertansif Kriz', 'I10', 'Kan basıncı > 180/120 mmHg, şiddetli baş ağrısı, görme bulanıklığı, burun kanaması', 'Kardiyoloji', 'Genel Dahiliye', 'SARI', 'Uç organ hasarı (kalp, beyin, böbrek) taranmalıdır.'),
('Açık Kırık / Eklem Çıkığı', 'T14.2', 'Ekstremitede anormal hareketlilik, açık yara, kemik fragmanı, şiddetli ağrı, deformite', 'Ortopedi ve Travmatoloji', 'Acil Tıp', 'SARI', 'Acil redüksiyon, atelleme ve enfeksiyon profilaksisi gerekir.'),
('Akut Menenjit', 'G03.9', 'Ense sertliği, yüksek ateş, fotofobi (ışıktan rahatsız olma), peteşiyal döküntü', 'Enfeksiyon Hastalıkları', 'Nöroloji', 'KIRMIZI', 'Acil lomber ponksiyon ve ampirik antibiyotik başlanmalıdır.'),
('Gastrointestinal Kanama', 'K92.2', 'Melena (katran renkli dışkı), hematemez (kahve telvesi kusma), baş dönmesi, anemi', 'Gastroenteroloji', 'Genel Cerrahi', 'KIRMIZI', 'Acil endoskopi ve kan transfüzyon hazırlığı yapılmalıdır.'),
('Akut Sinüzit / ÜSYE', 'J01.9', 'Yüzde basınç hissi, burun tıkanıklığı, hafif baş ağrısı, boğazda gıcıklanma', 'Kulak Burun Boğaz', 'Genel Dahiliye', 'YESIL', 'Ayaktan medikal tedavi ve istirahat yeterlidir.'),
('Basit Yumuşak Doku Travması', 'T14.0', 'Hafif burkulma, lokalize şişlik, hareketle minimal ağrı, dolaşım ve duyu normal', 'Ortopedi ve Travmatoloji', 'Acil Tıp', 'YESIL', 'Soğuk uygulama, elevasyon ve basit analjezik yeterlidir.');
