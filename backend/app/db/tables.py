"""SQLAlchemy veritabanı modelleri.
Kaynak şema database/init.sql'dir; PostgreSQL ve DB2 ile tam uyumludur.

Tablo Mimarisi:
- 4 Kart Tablosu: HastaDemografi, TibbiGecmis, AnlikVitaller, Sikayet
- 1 Master Tablo: HastaneLog (4 kartın ID'lerini bağlar ve AI kararını saklar)
- 1 ML Eğitim Tablosu: HastalikSevk (Hastalık -> Sevk Polikliniği Veri Seti)
"""

from datetime import date, time, datetime
from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Time, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class HastaDemografi(Base):
    """Kart 1: Temel Demografi"""
    __tablename__ = "hasta_demografi"
    __table_args__ = (Index("ix_demografi_kimlik", "kimlik_no"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isim: Mapped[str] = mapped_column(String(400), nullable=False)
    yas: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    boy: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    kilo: Mapped[float | None] = mapped_column(Numeric(5, 1, asdecimal=False), nullable=True)
    kan_grubu: Mapped[str] = mapped_column(String(10), default="BILINMIYOR", nullable=False)
    kimlik_turu: Mapped[str] = mapped_column(String(10), default="TC", nullable=False)
    kimlik_no: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # İlişki
    loglar: Mapped[list["HastaneLog"]] = relationship("HastaneLog", back_populates="demografi", cascade="all, delete-orphan")


class TibbiGecmis(Base):
    """Kart 2: Tıbbi Geçmiş"""
    __tablename__ = "tibbi_gecmis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kronik_rahatsizlik: Mapped[str | None] = mapped_column(String(2000), default="", nullable=True)
    surekli_ilac: Mapped[str | None] = mapped_column(String(2000), default="", nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # İlişki
    loglar: Mapped[list["HastaneLog"]] = relationship("HastaneLog", back_populates="tibbi_gecmis", cascade="all, delete-orphan")


class AnlikVitaller(Base):
    """Kart 3: Anlık Vitaller"""
    __tablename__ = "anlik_vitaller"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nabiz: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tansiyon_sistolik: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tansiyon_diyastolik: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    solunum: Mapped[int] = mapped_column(SmallInteger, default=16, nullable=False)
    ates: Mapped[float] = mapped_column(Numeric(4, 1, asdecimal=False), default=36.8, nullable=False)
    spo2: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    troponin: Mapped[float | None] = mapped_column(Numeric(6, 3, asdecimal=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # İlişki
    loglar: Mapped[list["HastaneLog"]] = relationship("HastaneLog", back_populates="vitaller", cascade="all, delete-orphan")


class Sikayet(Base):
    """Kart 4: Hasta Şikayeti"""
    __tablename__ = "hasta_sikayet"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ana_sikayet: Mapped[str] = mapped_column(Text, nullable=False)
    agri_skalasi: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # İlişki
    loglar: Mapped[list["HastaneLog"]] = relationship("HastaneLog", back_populates="sikayet", cascade="all, delete-orphan")


class HastaneLog(Base):
    """5. Master Tablo: Hastane Log (4 Kartı birbirine bağlayan ve AI kararını tutan tablo)"""
    __tablename__ = "hastane_log"
    __table_args__ = (
        UniqueConstraint("tarih", "sira_no", name="uq_log_tarih_sira"),
        Index("ix_log_tarih_durum", "tarih", "durum", "sira_no"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sira_no: Mapped[int] = mapped_column(Integer, nullable=False)
    tarih: Mapped[date] = mapped_column(Date, nullable=False)
    saat: Mapped[time] = mapped_column(Time, nullable=False)

    # 4 Kartın Referans Kodları (Foreign Keys)
    demografi_id: Mapped[int] = mapped_column(ForeignKey("hasta_demografi.id", ondelete="CASCADE"), nullable=False)
    tibbi_gecmis_id: Mapped[int] = mapped_column(ForeignKey("tibbi_gecmis.id", ondelete="CASCADE"), nullable=False)
    vitaller_id: Mapped[int] = mapped_column(ForeignKey("anlik_vitaller.id", ondelete="CASCADE"), nullable=False)
    sikayet_id: Mapped[int] = mapped_column(ForeignKey("hasta_sikayet.id", ondelete="CASCADE"), nullable=False)

    # Yapay Zekâ ve Triaj Kararları
    durum: Mapped[str] = mapped_column(String(20), nullable=False)  # KIRMIZI, SARI, YESIL
    risk_skoru: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)  # ESI 1-5
    onerilen_poliklinik: Mapped[str | None] = mapped_column(String(150), nullable=True)
    birim_uyumluluk_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    kritik_bulgu: Mapped[str | None] = mapped_column(String(1500), nullable=True)
    erken_uyari_notu: Mapped[str | None] = mapped_column(String(1500), nullable=True)
    aciklama: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    karar_kaynagi: Mapped[str] = mapped_column(String(50), default="LLM", nullable=False)
    news2_skoru: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    islendi: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # 4 Karta Erişim İlişkileri (Eager/Lazy Navigation)
    demografi: Mapped[HastaDemografi] = relationship("HastaDemografi", back_populates="loglar", lazy="joined")
    tibbi_gecmis: Mapped[TibbiGecmis] = relationship("TibbiGecmis", back_populates="loglar", lazy="joined")
    vitaller: Mapped[AnlikVitaller] = relationship("AnlikVitaller", back_populates="loglar", lazy="joined")
    sikayet: Mapped[Sikayet] = relationship("Sikayet", back_populates="loglar", lazy="joined")


class HastalikSevk(Base):
    """6. ML Eğitim ve Klinik Sevk Referans Tablosu (Hastalık -> Sevk Polikliniği Veri Seti)"""
    __tablename__ = "hastalik_sevk_referans"
    __table_args__ = (
        Index("ix_ml_hastalik", "hastalik_adi"),
        Index("ix_ml_birincil", "birincil_poliklinik"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hastalik_adi: Mapped[str] = mapped_column(String(200), nullable=False)
    icd10_kodu: Mapped[str | None] = mapped_column(String(20), nullable=True)
    semptomlar: Mapped[str] = mapped_column(String(2000), nullable=False)
    birincil_poliklinik: Mapped[str] = mapped_column(String(100), nullable=False)
    ikincil_poliklinik: Mapped[str | None] = mapped_column(String(100), nullable=True)
    varsayilan_triaj_kodu: Mapped[str] = mapped_column(String(20), nullable=False)  # KIRMIZI, SARI, YESIL
    aciklama: Mapped[str | None] = mapped_column(String(1000), nullable=True)
