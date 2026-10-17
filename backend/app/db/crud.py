"""Veritabanı CRUD operasyonları.
4 Kartın verilerini ve Master Hastane Log kaydını tek bir transaction içerisinde yönetir.
"""

import json
from datetime import date, datetime
from typing import Optional, List, Any
from sqlalchemy import case, func, select, desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.tables import HastaDemografi, TibbiGecmis, AnlikVitaller, Sikayet, HastaneLog

_SIRA_DENEME = 5


def _sonraki_sira_no(db: Session, tarih: date) -> int:
    """Günlük artan sıra numarasını hesaplar."""
    son = db.scalar(select(func.max(HastaneLog.sira_no)).where(HastaneLog.tarih == tarih))
    return (son or 0) + 1


def triaj_kaydi_olustur(db: Session, istek: Any, karar: Any, zaman: datetime) -> HastaneLog:
    """4 Kartı ve bu kartların kodlarını tutan Master HASTANE_LOG satırını tek transaction'da yazar.
    
    istek: 4 kart verisini içeren Pydantic nesnesi (demografi, tibbi_gecmis, vitaller, sikayet)
    karar: AI veya kural motoru tarafından üretilen TriajKarari nesnesi
    zaman: Kayıt anı (datetime)
    """
    # Girdi model_dump desteği (Pydantic v2 veya dict)
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

    # Karar alanlarını çıkart
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
    karar_kaynagi = getattr(karar, "karar_kaynagi", "WATSONX")
    news2_skoru = getattr(karar, "news2_skoru", 0)

    # Transaction içinde kayıt
    for deneme in range(_SIRA_DENEME):
        try:
            sira_no = _sonraki_sira_no(db, zaman.date())

            # 4 Kart Tablosunu Oluştur
            demografi = HastaDemografi(
                isim=demo_data.get("isim", ""),
                yas=int(demo_data.get("yas", 0)),
                boy=demo_data.get("boy"),
                kilo=demo_data.get("kilo"),
                kan_grubu=str(demo_data.get("kan_grubu", "BILINMIYOR")),
                kimlik_turu=str(demo_data.get("kimlik_turu", "TC")),
                kimlik_no=str(demo_data.get("kimlik_no", "")),
            )
            tibbi_gecmis = TibbiGecmis(
                kronik_rahatsizlik=gecmis_data.get("kronik_rahatsizlik", ""),
                surekli_ilac=gecmis_data.get("surekli_ilac", ""),
            )
            vitaller = AnlikVitaller(
                nabiz=int(vitaller_data.get("nabiz", 80)),
                tansiyon_sistolik=int(vitaller_data.get("tansiyon_sistolik", 120)),
                tansiyon_diyastolik=int(vitaller_data.get("tansiyon_diyastolik", 80)),
                solunum=int(vitaller_data.get("solunum", 16)),
                ates=float(vitaller_data.get("ates", 36.8)),
                spo2=int(vitaller_data.get("spo2", 98)),
                troponin=vitaller_data.get("troponin"),
            )
            sikayet = Sikayet(
                ana_sikayet=str(sikayet_data.get("ana_sikayet", "")),
                agri_skalasi=int(sikayet_data.get("agri_skalasi", 1)),
            )

            # Master Log Nesnesi (4 kart ilişkilendirilir)
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
    """Acil servis triaj kuyruğu: Öncelikle KIRMIZI, sonra SARI, sonra YESIL sıralamasıyla getirir."""
    if tarih is None:
        tarih = date.today()

    # Aciliyet sıralama ağırlığı: KIRMIZI=1, SARI=2, YESIL=3
    oncelik_sirasi = case(
        (HastaneLog.durum == "KIRMIZI", 1),
        (HastaneLog.durum == "SARI", 2),
        (HastaneLog.durum == "YESIL", 3),
        else_=4,
    )

    query = select(HastaneLog).where(HastaneLog.tarih == tarih)
    if durum:
        query = query.where(HastaneLog.durum == durum.upper())

    query = query.order_by(oncelik_sirasi, HastaneLog.sira_no).limit(limit)
    return list(db.scalars(query).all())


def log_detay_getir(db: Session, log_id: int) -> Optional[HastaneLog]:
    """Belirli bir başvuruya ait 4 kart ve AI karar detaylarını getirir."""
    return db.scalar(select(HastaneLog).where(HastaneLog.id == log_id))
