"""Database CRUD operations.
Manages the four intake cards, the master hospital log, and the ML referral dataset.
"""

import json
from datetime import date, datetime
from typing import Optional, List, Any
from sqlalchemy import func, select, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.tables import HastaDemografi, TibbiGecmis, AnlikVitaller, Sikayet, HastaneLog, HastalikSevk

_SIRA_DENEME = 5


def _sonraki_sira_no(db: Session, tarih: date) -> int:
    """Calculate the next sequential number for the day."""
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
    if isinstance(birim_uyumluluk, (list, dict)):
        birim_uyumluluk_json = json.dumps(
            [item.model_dump() if hasattr(item, "model_dump") else item for item in birim_uyumluluk]
            if isinstance(birim_uyumluluk, list) else birim_uyumluluk,
            ensure_ascii=False
        )
    else:
        birim_uyumluluk_json = getattr(karar, "birim_uyumluluk_json", None)

    kritik_bulgu = getattr(karar, "kritik_bulgu", None)
    erken_uyari_notu = getattr(karar, "erken_uyari_notu", None)
    aciklama = getattr(karar, "aciklama", None)
    karar_kaynagi = getattr(karar, "karar_kaynagi", "LLM")
    news2_skoru = getattr(karar, "news2_skoru", 0)

    for deneme in range(_SIRA_DENEME):
        try:
            sira_no = _sonraki_sira_no(db, zaman.date())

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
            )
            sikayet = Sikayet(
                ana_sikayet=str(sikayet_data.get("ana_sikayet", "")),
                agri_skalasi=int(sikayet_data.get("agri_skalasi", 1)),
            )

            log = HastaneLog(
                sira_no=sira_no,
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

            db.add(log)
            db.commit()
            db.refresh(log)
            return log

        except IntegrityError:
            db.rollback()
            if deneme == _SIRA_DENEME - 1:
                raise


def kuyruk_getir(db: Session, tarih: Optional[date] = None, durum: Optional[str] = None, limit: int = 100) -> List[HastaneLog]:
    """Return the emergency triage queue ordered by RED, YELLOW, and GREEN status."""
    if tarih is None:
        tarih = date.today()

    query = select(HastaneLog).where(HastaneLog.tarih == tarih)
    if durum:
        query = query.where(HastaneLog.durum == durum.upper())

    query = query.order_by(HastaneLog.risk_skoru, HastaneLog.sira_no).limit(limit)
    return list(db.scalars(query).all())


def tum_triaj_kayitlarini_getir(db: Session) -> List[HastaneLog]:
    """Return every saved triage record, newest first."""
    query = select(HastaneLog).order_by(
        HastaneLog.tarih.desc(),
        HastaneLog.saat.desc(),
        HastaneLog.sira_no.desc(),
    )
    return list(db.scalars(query).all())


def log_detay_getir(db: Session, log_id: int) -> Optional[HastaneLog]:
    """Return the four cards and AI decision for a specific visit."""
    return db.scalar(select(HastaneLog).where(HastaneLog.id == log_id))


def durum_guncelle(db: Session, log: HastaneLog, durum: str, aciklama: Optional[str] = None) -> HastaneLog:
    """Save a staff member's manual triage status update."""
    log.durum = durum.upper()
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
