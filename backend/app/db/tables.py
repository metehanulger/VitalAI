"""DB tabloları. Kaynak şema database/init.sql'dir; buradaki tanımlar onunla aynı tutulmalı.

Tablo adları küçük harfle yazılır; DB2 bunları büyük harfe çevirir (HASTANE_LOG vb.).
"""

from datetime import date, time

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class HastaDemografi(Base):
    """Kart 1: Temel Demografi"""

    __tablename__ = "hasta_demografi"
    __table_args__ = (Index("ix_demografi_kimlik", "kimlik_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isim: Mapped[str] = mapped_column(String(400))
    yas: Mapped[int] = mapped_column(SmallInteger)
    boy: Mapped[int | None] = mapped_column(SmallInteger)
    kilo: Mapped[float | None] = mapped_column(Numeric(5, 1, asdecimal=False))
    kan_grubu: Mapped[str] = mapped_column(String(10), default="BILINMIYOR")
    kimlik_turu: Mapped[str] = mapped_column(String(10))
    kimlik_no: Mapped[str] = mapped_column(String(20))


class TibbiGecmis(Base):
    """Kart 2: Tıbbi Geçmiş"""

    __tablename__ = "tibbi_gecmis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kronik_rahatsizlik: Mapped[str | None] = mapped_column(String(1600))
    surekli_ilac: Mapped[str | None] = mapped_column(String(1600))


class AnlikVitaller(Base):
    """Kart 3: Anlık Vitaller"""

    __tablename__ = "anlik_vitaller"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nabiz: Mapped[int] = mapped_column(SmallInteger)
    tansiyon_sistolik: Mapped[int] = mapped_column(SmallInteger)
    tansiyon_diastolik: Mapped[int] = mapped_column(SmallInteger)
    solunum: Mapped[int] = mapped_column(SmallInteger)
    ates: Mapped[float] = mapped_column(Numeric(4, 1, asdecimal=False))
    spo2: Mapped[int] = mapped_column(SmallInteger)


class Sikayet(Base):
    """Kart 4: Şikayet"""

    __tablename__ = "sikayet"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ana_sikayet: Mapped[str] = mapped_column(String(3200))
    agri_skalasi: Mapped[int] = mapped_column(SmallInteger)


class HastaneLog(Base):
    """Hastane log verisi: 4 kartın kodları + hasta durumu, tarih, saat, sıra no."""

    __tablename__ = "hastane_log"
    __table_args__ = (UniqueConstraint("tarih", "sira_no", name="uq_log_tarih_sira"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    demografi_id: Mapped[int] = mapped_column(ForeignKey("hasta_demografi.id"))
    tibbi_gecmis_id: Mapped[int] = mapped_column(ForeignKey("tibbi_gecmis.id"))
    vitaller_id: Mapped[int] = mapped_column(ForeignKey("anlik_vitaller.id"))
    sikayet_id: Mapped[int] = mapped_column(ForeignKey("sikayet.id"))
    hasta_durumu: Mapped[str] = mapped_column(String(10))
    aciklama: Mapped[str | None] = mapped_column(String(1000))
    karar_kaynagi: Mapped[str] = mapped_column(String(20))
    tarih: Mapped[date] = mapped_column(Date)
    saat: Mapped[time] = mapped_column(Time)
    sira_no: Mapped[int] = mapped_column(Integer)

    demografi: Mapped[HastaDemografi] = relationship(lazy="joined")
    tibbi_gecmis: Mapped[TibbiGecmis] = relationship(lazy="joined")
    vitaller: Mapped[AnlikVitaller] = relationship(lazy="joined")
    sikayet: Mapped[Sikayet] = relationship(lazy="joined")

    @property
    def kodlar(self) -> dict[str, int]:
        return {
            "demografi_id": self.demografi_id,
            "tibbi_gecmis_id": self.tibbi_gecmis_id,
            "vitaller_id": self.vitaller_id,
            "sikayet_id": self.sikayet_id,
        }
