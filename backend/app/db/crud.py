"""Database CRUD operations.
Manages the four intake cards, the master hospital log, and the ML referral dataset.
"""

from datetime import date, datetime
from typing import Optional, List, Any
from sqlalchemy import func, select, or_, text
from sqlalchemy.orm import Session

from app.core.config import yerel_simdi
from app.db.tables import HastaDemografi, TibbiGecmis, AnlikVitaller, Sikayet, HastaneLog, HastalikSevk

# Namespace for pg_advisory_xact_lock(namespace, key); the key is the day as YYYYMMDD.
_SIRA_KILIT_ALANI = 7301

# ESI scores that are consistent with each color status (1 is most urgent).
_DURUM_ESI = {"KIRMIZI": (1,), "SARI": (2, 3), "YESIL": (4, 5)}


def _kirp(deger: Any, sutun) -> Optional[str]:
    """Trim free text (often LLM output) to the column's length so the insert cannot fail."""
    if deger is None:
        return None
    metin = str(deger)
    uzunluk = getattr(sutun.type, "length", None)
    return metin[:uzunluk] if uzunluk else metin


def _sonraki_sira_no(db: Session, tarih: date) -> int:
    """Return the next queue number for the day.

    A transaction-level advisory lock serializes concurrent inserts for the same
    day, so MAX + 1 cannot collide. The lock is released on commit or rollback.
    """
    db.execute(
        text("SELECT pg_advisory_xact_lock(:alan, :anahtar)"),
        {"alan": _SIRA_KILIT_ALANI, "anahtar": int(tarih.strftime("%Y%m%d"))},
    )
    son = db.scalar(select(func.max(HastaneLog.sira_no)).where(HastaneLog.tarih == tarih))
    return (son or 0) + 1


def triaj_kaydi_olustur(db: Session, istek: Any, karar: Any, zaman: datetime) -> HastaneLog:
    """Write the four cards and their IDs to the master hospital log in one transaction."""
    def _to_dict(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        elif hasattr(obj, "dict"):
            return obj.dict()
        elif isinstance(obj, dict):
            return obj
        return obj.__dict__

    demo_data = _to_dict(istek.demografi)
    gecmis_data = _to_dict(istek.tibbi_gecmis)
    vitaller_data = _to_dict(istek.vitaller)
    sikayet_data = _to_dict(istek.sikayet)

    durum = getattr(karar, "durum", "SARI")
    if hasattr(durum, "value"):
        durum = durum.value
    durum = str(durum).upper()

    risk_skoru = getattr(karar, "risk_skoru", 3)
    onerilen_poliklinik = getattr(karar, "onerilen_poliklinik", None)
    birim_uyumluluk = getattr(karar, "birim_uyumluluk_siralamasi", None)
    if isinstance(birim_uyumluluk, dict):
        birim_uyumluluk = [birim_uyumluluk]
    birim_uyumluluk_json = (
        [item.model_dump() if hasattr(item, "model_dump") else item for item in birim_uyumluluk]
        if isinstance(birim_uyumluluk, list)
        else getattr(karar, "birim_uyumluluk_json", None)
    )

    kolon = HastaneLog.__table__.c
    onerilen_poliklinik = _kirp(onerilen_poliklinik, kolon.onerilen_poliklinik)
    kritik_bulgu = _kirp(getattr(karar, "kritik_bulgu", None), kolon.kritik_bulgu)
    erken_uyari_notu = _kirp(getattr(karar, "erken_uyari_notu", None), kolon.erken_uyari_notu)
    aciklama = _kirp(getattr(karar, "aciklama", None), kolon.aciklama)
    karar_kaynagi = _kirp(getattr(karar, "karar_kaynagi", "LLM"), kolon.karar_kaynagi)
    news2_skoru = getattr(karar, "news2_skoru", 0)

    demografi = HastaDemografi(
        isim=demo_data.get("isim", ""),
        yas=int(demo_data.get("yas", 0)),
        boy=demo_data.get("boy"),
        kilo=demo_data.get("kilo"),
        kan_grubu=str(demo_data.get("kan_grubu", "BILINMIYOR")),
        kimlik_turu=getattr(demo_data.get("kimlik_turu", "TC"), "value", demo_data.get("kimlik_turu", "TC")),
        kimlik_no=str(demo_data.get("kimlik_no", "")),
    )
    tibbi_gecmis = TibbiGecmis(
        kronik_rahatsizlik=gecmis_data.get("kronik_rahatsizlik", ""),
        surekli_ilac=gecmis_data.get("surekli_ilac", ""),
    )
    vitaller = AnlikVitaller(
        nabiz=int(vitaller_data.get("nabiz", 80)),
        tansiyon_sistolik=int(vitaller_data.get("tansiyon_sistolik", 120)),
        tansiyon_diyastolik=int(vitaller_data.get("tansiyon_diastolik", 80)),
        solunum=int(vitaller_data.get("solunum", 16)),
        ates=float(vitaller_data.get("ates", 36.8)),
        spo2=int(vitaller_data.get("spo2", 98)),
        troponin=vitaller_data.get("troponin"),
        bilinc=str(vitaller_data.get("bilinc") or "A").upper(),
        ek_oksijen=bool(vitaller_data.get("ek_oksijen", False)),
    )
    sikayet = Sikayet(
        ana_sikayet=str(sikayet_data.get("ana_sikayet", "")),
        agri_skalasi=int(sikayet_data.get("agri_skalasi", 1)),
    )

    log = HastaneLog(
        tarih=zaman.date(),
        saat=zaman.time(),
        demografi=demografi,
        tibbi_gecmis=tibbi_gecmis,
        vitaller=vitaller,
        sikayet=sikayet,
        durum=durum,
        risk_skoru=risk_skoru,
        onerilen_poliklinik=onerilen_poliklinik,
        birim_uyumluluk_json=birim_uyumluluk_json,
        kritik_bulgu=kritik_bulgu,
        erken_uyari_notu=erken_uyari_notu,
        aciklama=aciklama,
        karar_kaynagi=karar_kaynagi,
        news2_skoru=news2_skoru,
        islendi=0,
    )

    try:
        # Taken last so the day's lock is held only for the insert and commit.
        log.sira_no = _sonraki_sira_no(db, log.tarih)
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(log)
    return log


def kuyruk_getir(db: Session, tarih: Optional[date] = None, durum: Optional[str] = None, limit: int = 100) -> List[HastaneLog]:
    """Return the emergency triage queue ordered by RED, YELLOW, and GREEN status."""
    if tarih is None:
        tarih = yerel_simdi().date()

    query = select(HastaneLog).where(HastaneLog.tarih == tarih)
    if durum:
        query = query.where(HastaneLog.durum == durum.upper())

    query = query.order_by(HastaneLog.risk_skoru, HastaneLog.sira_no).limit(limit)
    return list(db.scalars(query).all())


def triaj_kayit_sayisi(db: Session) -> int:
    """Return the total number of saved triage records."""
    return db.scalar(select(func.count()).select_from(HastaneLog)) or 0


def tum_triaj_kayitlarini_getir(db: Session, limit: int = 50, offset: int = 0) -> List[HastaneLog]:
    """Return one page of saved triage records, newest first."""
    query = (
        select(HastaneLog)
        .order_by(HastaneLog.tarih.desc(), HastaneLog.saat.desc(), HastaneLog.sira_no.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query).all())


def log_detay_getir(db: Session, log_id: int) -> Optional[HastaneLog]:
    """Return the four cards and AI decision for a specific visit."""
    return db.scalar(select(HastaneLog).where(HastaneLog.id == log_id))


def durum_guncelle(db: Session, log: HastaneLog, durum: str, aciklama: Optional[str] = None) -> HastaneLog:
    """Save a staff member's manual triage status update.

    The ESI score is moved into the new status's range when it no longer fits, so
    the queue order and the displayed urgency follow the manual decision.
    """
    log.durum = durum.upper()
    izinli = _DURUM_ESI.get(log.durum)
    if izinli and log.risk_skoru not in izinli:
        log.risk_skoru = izinli[-1] if log.risk_skoru > izinli[-1] else izinli[0]
    log.karar_kaynagi = "MANUEL"
    if aciklama is not None:
        log.aciklama = aciklama
    db.commit()
    db.refresh(log)
    return log


def ml_egitim_veri_setini_getir(db: Session, limit: int = 5000) -> List[HastalikSevk]:
    """Return disease-to-clinic reference rows for ML training."""
    return list(db.scalars(select(HastalikSevk).limit(limit)).all())


def semptoma_gore_sevk_ara(db: Session, anahtar_kelime: str) -> List[HastalikSevk]:
    """Search for matching conditions and recommended clinics by complaint or symptom."""
    query = select(HastalikSevk).where(
        or_(
            HastalikSevk.semptomlar.ilike(f"%{anahtar_kelime}%"),
            HastalikSevk.hastalik_adi.ilike(f"%{anahtar_kelime}%")
        )
    )
    return list(db.scalars(query).all())


def yeni_hastalik_sevk_ekle(
    db: Session,
    hastalik_adi: str,
    semptomlar: str,
    birincil_poliklinik: str,
    varsayilan_triaj_kodu: str = "SARI",
    ikincil_poliklinik: Optional[str] = None,
    icd10_kodu: Optional[str] = None,
    aciklama: Optional[str] = None
) -> HastalikSevk:
    """Save a disease-to-clinic mapping for ML training."""
    kayit = HastalikSevk(
        hastalik_adi=hastalik_adi,
        semptomlar=semptomlar,
        birincil_poliklinik=birincil_poliklinik,
        ikincil_poliklinik=ikincil_poliklinik,
        varsayilan_triaj_kodu=varsayilan_triaj_kodu,
        icd10_kodu=icd10_kodu,
        aciklama=aciklama,
    )
    db.add(kayit)
    db.commit()
    db.refresh(kayit)
    return kayit
