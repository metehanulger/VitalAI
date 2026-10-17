import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from app.db.connection import db_manager
from app.models.schema import HastaKabulGirdisi
from app.models.llm import LLMTriageOutput, HastaneLogResponse, BirimUyumluluk

logger = logging.getLogger("triage_repository")

SQLITE_DB_PATH = "triage_local.sqlite3"

def init_tables():
    """Yerel SQLite veritabanında 4 kart ve 1 hastane log tablosunu oluşturur."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cur = conn.cursor()
    
    # 1. Kart Tablosu: Temel Demografi
    cur.execute("""
    CREATE TABLE IF NOT EXISTS TEMEL_DEMOGRAFI (
        demografi_id TEXT PRIMARY KEY,
        isim TEXT,
        yas INTEGER,
        boy REAL,
        kilo REAL,
        kan_grubu TEXT,
        kimlik_no TEXT,
        created_at TEXT
    )
    """)
    
    # 2. Kart Tablosu: Tıbbi Geçmiş
    cur.execute("""
    CREATE TABLE IF NOT EXISTS TIBBI_GECMIS (
        tibbi_gecmis_id TEXT PRIMARY KEY,
        kronik_rahatsizlik TEXT,
        surekli_ilac TEXT,
        created_at TEXT
    )
    """)
    
    # 3. Kart Tablosu: Anlık Vitaller
    cur.execute("""
    CREATE TABLE IF NOT EXISTS ANLIK_VITALLER (
        vitaller_id TEXT PRIMARY KEY,
        nabiz REAL,
        tansiyon_sistolik REAL,
        tansiyon_diyastolik REAL,
        solunum REAL,
        ates REAL,
        spo2 REAL,
        troponin REAL,
        created_at TEXT
    )
    """)
    
    # 4. Kart Tablosu: Hasta Şikayeti
    cur.execute("""
    CREATE TABLE IF NOT EXISTS HASTA_SIKAYET (
        sikayet_id TEXT PRIMARY KEY,
        ana_sikayet TEXT,
        agri_skalasi INTEGER,
        created_at TEXT
    )
    """)
    
    # 5. Tablo: Hastane Log Verisi (4 kartın kodlarını ve AI triaj kararını tutar)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS HASTANE_LOG (
        log_id TEXT PRIMARY KEY,
        demografi_id TEXT,
        tibbi_gecmis_id TEXT,
        vitaller_id TEXT,
        sikayet_id TEXT,
        risk_skoru INTEGER,
        renk_kodu TEXT,
        onerilen_poliklinik TEXT,
        uyumlu_birimler_json TEXT,
        kritik_bulgu TEXT,
        erken_uyari_notu TEXT,
        ml_risk_skoru REAL,
        ai_provider TEXT,
        created_at TEXT
    )
    """)
    
    conn.commit()
    conn.close()

# Tabloları başlat
init_tables()

class TriageRepository:
    """
    4 Kartın verilerini ve 5. Hastane Log tablosunu yöneten Repository katmanı.
    """

    @staticmethod
    def save_triage_flow(
        hasta_girdisi: HastaKabulGirdisi,
        llm_output: LLMTriageOutput,
        ml_risk_skoru: Optional[float] = None,
        provider: str = "Google-Gemini"
    ) -> HastaneLogResponse:
        now_str = datetime.utcnow().isoformat()
        
        # Benzersiz ID'ler oluştur
        demografi_id = hasta_girdisi.demografi.id or f"DEM-{uuid.uuid4().hex[:8].upper()}"
        tibbi_gecmis_id = hasta_girdisi.tibbi_gecmis.id or f"GEC-{uuid.uuid4().hex[:8].upper()}"
        vitaller_id = hasta_girdisi.vitaller.id or f"VIT-{uuid.uuid4().hex[:8].upper()}"
        sikayet_id = hasta_girdisi.sikayet.id or f"SIK-{uuid.uuid4().hex[:8].upper()}"
        log_id = f"LOG-{uuid.uuid4().hex[:8].upper()}"

        uyumlu_birimler_json = json.dumps([b.dict() for b in llm_output.Birim_Uyumluluk_Siralamasi], ensure_ascii=False)

        # 1. DB2 Bağlantısı varsa kaydet
        if db_manager.is_connected:
            try:
                import ibm_db
                # 1. Demografi
                sql1 = "INSERT INTO TEMEL_DEMOGRAFI (DEMOGRAFI_ID, ISIM, YAS, BOY, KILO, KAN_GRUBU, KIMLIK_NO) VALUES (?, ?, ?, ?, ?, ?, ?)"
                st1 = ibm_db.prepare(db_manager._conn, sql1)
                ibm_db.execute(st1, (demografi_id, hasta_girdisi.demografi.isim, hasta_girdisi.demografi.yas, hasta_girdisi.demografi.boy, hasta_girdisi.demografi.kilo, hasta_girdisi.demografi.kan_grubu, hasta_girdisi.demografi.kimlik_no))

                # 2. Geçmiş
                sql2 = "INSERT INTO TIBBI_GECMIS (TIBBI_GECMIS_ID, KRONIK_RAHATSIZLIK, SUREKLI_ILAC) VALUES (?, ?, ?)"
                st2 = ibm_db.prepare(db_manager._conn, sql2)
                ibm_db.execute(st2, (tibbi_gecmis_id, hasta_girdisi.tibbi_gecmis.kronik_rahatsizlik, hasta_girdisi.tibbi_gecmis.surekli_ilac))

                # 3. Vitaller
                sql3 = "INSERT INTO ANLIK_VITALLER (VITALLER_ID, NABIZ, TANSIYON_SISTOLIK, TANSIYON_DIYASTOLIK, SOLUNUM, ATES, SPO2, TROPONIN) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                st3 = ibm_db.prepare(db_manager._conn, sql3)
                ibm_db.execute(st3, (vitaller_id, hasta_girdisi.vitaller.nabiz, hasta_girdisi.vitaller.tansiyon_sistolik, hasta_girdisi.vitaller.tansiyon_diyastolik, hasta_girdisi.vitaller.solunum, hasta_girdisi.vitaller.ates, hasta_girdisi.vitaller.spo2, hasta_girdisi.vitaller.troponin))

                # 4. Şikayet
                sql4 = "INSERT INTO HASTA_SIKAYET (SIKAYET_ID, ANA_SIKAYET, AGRI_SKALASI) VALUES (?, ?, ?)"
                st4 = ibm_db.prepare(db_manager._conn, sql4)
                ibm_db.execute(st4, (sikayet_id, hasta_girdisi.sikayet.ana_sikayet, hasta_girdisi.sikayet.agri_skalasi))

                # 5. Hastane Log (Master)
                sql5 = "INSERT INTO HASTANE_LOG (LOG_ID, DEMOGRAFI_ID, TIBBI_GECMIS_ID, VITALLER_ID, SIKAYET_ID, RISK_SKORU, RENK_KODU, ONERILEN_POLIKLINIK, UYUMLU_BIRIMLER_JSON, KRITIK_BULGU, ERKEN_UYARI_NOTU, ML_RISK_SKORU, AI_PROVIDER) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
                st5 = ibm_db.prepare(db_manager._conn, sql5)
                ibm_db.execute(st5, (log_id, demografi_id, tibbi_gecmis_id, vitaller_id, sikayet_id, llm_output.Risk_Skoru, llm_output.Renk_Kodu, llm_output.Onerilen_Poliklinik, uyumlu_birimler_json, llm_output.Kritik_Bulgu, llm_output.Erken_Uyari_Notu, ml_risk_skoru, provider))
                logger.info(f"DB2'ye 4 kart ve log verisi başarıyla işlendi: Log ID={log_id}")
            except Exception as e:
                logger.warning(f"DB2 yazma hatası ({e}); SQLite yedek moduna kaydediliyor.")

        # 2. SQLite Kaydı
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cur = conn.cursor()
            
            # Kart 1
            cur.execute("""
            INSERT OR REPLACE INTO TEMEL_DEMOGRAFI VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (demografi_id, hasta_girdisi.demografi.isim, hasta_girdisi.demografi.yas, hasta_girdisi.demografi.boy, hasta_girdisi.demografi.kilo, hasta_girdisi.demografi.kan_grubu, hasta_girdisi.demografi.kimlik_no, now_str))

            # Kart 2
            cur.execute("""
            INSERT OR REPLACE INTO TIBBI_GECMIS VALUES (?, ?, ?, ?)
            """, (tibbi_gecmis_id, hasta_girdisi.tibbi_gecmis.kronik_rahatsizlik, hasta_girdisi.tibbi_gecmis.surekli_ilac, now_str))

            # Kart 3
            cur.execute("""
            INSERT OR REPLACE INTO ANLIK_VITALLER VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (vitaller_id, hasta_girdisi.vitaller.nabiz, hasta_girdisi.vitaller.tansiyon_sistolik, hasta_girdisi.vitaller.tansiyon_diyastolik, hasta_girdisi.vitaller.solunum, hasta_girdisi.vitaller.ates, hasta_girdisi.vitaller.spo2, hasta_girdisi.vitaller.troponin, now_str))

            # Kart 4
            cur.execute("""
            INSERT OR REPLACE INTO HASTA_SIKAYET VALUES (?, ?, ?, ?)
            """, (sikayet_id, hasta_girdisi.sikayet.ana_sikayet, hasta_girdisi.sikayet.agri_skalasi, now_str))

            # 5. Hastane Log Tablosu
            cur.execute("""
            INSERT OR REPLACE INTO HASTANE_LOG VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log_id, demografi_id, tibbi_gecmis_id, vitaller_id, sikayet_id, llm_output.Risk_Skoru, llm_output.Renk_Kodu, llm_output.Onerilen_Poliklinik, uyumlu_birimler_json, llm_output.Kritik_Bulgu, llm_output.Erken_Uyari_Notu, ml_risk_skoru, provider, now_str))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"SQLite yazma hatası: {e}")

        return HastaneLogResponse(
            log_id=log_id,
            demografi_id=demografi_id,
            tibbi_gecmis_id=tibbi_gecmis_id,
            vitaller_id=vitaller_id,
            sikayet_id=sikayet_id,
            Risk_Skoru=llm_output.Risk_Skoru,
            Renk_Kodu=llm_output.Renk_Kodu,
            Onerilen_Poliklinik=llm_output.Onerilen_Poliklinik,
            Birim_Uyumluluk_Siralamasi=llm_output.Birim_Uyumluluk_Siralamasi,
            Kritik_Bulgu=llm_output.Kritik_Bulgu,
            Erken_Uyari_Notu=llm_output.Erken_Uyari_Notu,
            tarih_saat=now_str,
            ai_provider=provider
        )

    @staticmethod
    def get_logs(limit: int = 50) -> List[HastaneLogResponse]:
        """Hastane log tablosundaki kayıtları listeler."""
        logs = []
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            cur = conn.cursor()
            cur.execute("""
            SELECT log_id, demografi_id, tibbi_gecmis_id, vitaller_id, sikayet_id,
                   risk_skoru, renk_kodu, onerilen_poliklinik, uyumlu_birimler_json,
                   kritik_bulgu, erken_uyari_notu, ai_provider, created_at
            FROM HASTANE_LOG
            ORDER BY created_at DESC
            LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            for r in rows:
                birimler_raw = json.loads(r[8]) if r[8] else []
                birimler = [BirimUyumluluk(**b) for b in birimler_raw]
                logs.append(HastaneLogResponse(
                    log_id=r[0],
                    demografi_id=r[1],
                    tibbi_gecmis_id=r[2],
                    vitaller_id=r[3],
                    sikayet_id=r[4],
                    Risk_Skoru=r[5],
                    Renk_Kodu=r[6],
                    Onerilen_Poliklinik=r[7],
                    Birim_Uyumluluk_Siralamasi=birimler,
                    Kritik_Bulgu=r[9],
                    Erken_Uyari_Notu=r[10],
                    ai_provider=r[11],
                    tarih_saat=r[12]
                ))
            conn.close()
        except Exception as e:
            logger.error(f"Log okuma hatası: {e}")
        return logs
