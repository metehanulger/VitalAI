from datetime import date, datetime

from sqlalchemy import case, func, literal_column, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.metin import bayt_kirp
from app.core.triage import TriajKarari
from app.db.tables import AnlikVitaller, HastaDemografi, HastaneLog, Sikayet, TibbiGecmis
from app.models.schemas import TriajIstek

_SIRA_DENEME = 3


def _sonraki_sira_no(db: Session, tarih: date) -> int:
    son = db.scalar(select(func.max(HastaneLog.sira_no)).where(HastaneLog.tarih == tarih))
    return (son or 0) + 1


def triaj_kaydi_olustur(db: Session, istek: TriajIstek, karar: TriajKarari, zaman: datetime) -> HastaneLog:
    """4 kartı ve onların kodlarını tutan log satırını tek transaction'da yazar."""
    for deneme in range(_SIRA_DENEME):
        log = HastaneLog(
            demografi=HastaDemografi(**istek.demografi.model_dump(mode="json")),
            tibbi_gecmis=TibbiGecmis(**istek.tibbi_gecmis.model_dump()),
            vitaller=AnlikVitaller(**istek.vitaller.model_dump()),
            sikayet=Sikayet(**istek.sikayet.model_dump()),
            hasta_durumu=karar.durum,
            aciklama=bayt_kirp(karar.aciklama, 1000),
            karar_kaynagi=karar.kaynak,
            tarih=zaman.date(),
            saat=zaman.time(),
            sira_no=_sonraki_sira_no(db, zaman.date()),
        )
        db.add(log)
        try:
            db.commit()
            return log
        except IntegrityError:
            # Aynı anda gelen iki başvuru aynı sıra no'yu aldıysa (UQ_LOG_TARIH_SIRA) tekrar dene
            db.rollback()
            if deneme == _SIRA_DENEME - 1:
                raise
    raise AssertionError("ulaşılamaz")


def triaj_getir(db: Session, log_id: int) -> HastaneLog | None:
    return db.get(HastaneLog, log_id)


def kuyruk_listele(db: Session, tarih: date, durum: str | None, limit: int) -> list[HastaneLog]:
    # THEN değerleri sabit yazılır: DB2 CASE içinde tipsiz parametre (?) kabul etmez
    oncelik = case(
        (HastaneLog.hasta_durumu == "KIRMIZI", literal_column("0")),
        (HastaneLog.hasta_durumu == "SARI", literal_column("1")),
        else_=literal_column("2"),
    )
    sorgu = select(HastaneLog).where(HastaneLog.tarih == tarih)
    if durum:
        sorgu = sorgu.where(HastaneLog.hasta_durumu == durum)
    sorgu = sorgu.order_by(oncelik, HastaneLog.sira_no).limit(limit)
    return list(db.scalars(sorgu).unique())


def durum_guncelle(db: Session, log: HastaneLog, durum: str, aciklama: str | None) -> HastaneLog:
    log.hasta_durumu = durum
    log.karar_kaynagi = "MANUEL"
    if aciklama:
        log.aciklama = bayt_kirp(aciklama, 1000)
    db.commit()
    return log
