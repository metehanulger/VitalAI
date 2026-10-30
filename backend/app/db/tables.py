"""SQLAlchemy database models (PostgreSQL).
These models are the single schema definition; Alembic migrations in
backend/migrations are generated from them and tests check that both stay in sync.
CHECK limits mirror the Pydantic input limits in app/models/schemas.py.

Tablo Mimarisi:
- 4 Kart Tablosu: HastaDemografi, TibbiGecmis, AnlikVitaller, Sikayet
- 1 master table: HastaneLog (links the four card IDs and stores the AI decision)
- 1 ML training table: HastalikSevk (condition-to-clinic reference dataset)
"""

from datetime import date, time, datetime
from typing import Any
from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, Numeric, SmallInteger, String, Text,
    Time, UniqueConstraint, false, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


class HastaDemografi(Base):
    """Card 1: Basic demographics."""
    __tablename__ = "hasta_demografi"
    __table_args__ = (
        Index("ix_demografi_kimlik", "kimlik_no"),
        CheckConstraint("yas BETWEEN 0 AND 130", name="ck_demo_yas"),
        CheckConstraint("boy IS NULL OR boy BETWEEN 20 AND 260", name="ck_demo_boy"),
        CheckConstraint("kilo IS NULL OR kilo BETWEEN 0.5 AND 400", name="ck_demo_kilo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    isim: Mapped[str] = mapped_column(String(400), nullable=False)
    yas: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    boy: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    kilo: Mapped[float | None] = mapped_column(Numeric(5, 1, asdecimal=False), nullable=True)
    kan_grubu: Mapped[str] = mapped_column(String(10), default="BILINMIYOR", nullable=False)
    kimlik_turu: Mapped[str] = mapped_column(String(10), default="TC", nullable=False)
    kimlik_no: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    loglar: Mapped[list["HastaneLog"]] = relationship("HastaneLog", back_populates="demografi", cascade="all, delete-orphan")


class TibbiGecmis(Base):
    """Card 2: Medical history."""
    __tablename__ = "tibbi_gecmis"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kronik_rahatsizlik: Mapped[str | None] = mapped_column(String(2000), default="", nullable=True)
    surekli_ilac: Mapped[str | None] = mapped_column(String(2000), default="", nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    loglar: Mapped[list["HastaneLog"]] = relationship("HastaneLog", back_populates="tibbi_gecmis", cascade="all, delete-orphan")


class AnlikVitaller(Base):
    """Card 3: Current vital signs."""
    __tablename__ = "anlik_vitaller"
    __table_args__ = (
        CheckConstraint("nabiz BETWEEN 20 AND 300", name="ck_vit_nabiz"),
        CheckConstraint("tansiyon_sistolik BETWEEN 40 AND 300", name="ck_vit_sistolik"),
        CheckConstraint("tansiyon_diyastolik BETWEEN 20 AND 200", name="ck_vit_diyastolik"),
        CheckConstraint("solunum BETWEEN 4 AND 80", name="ck_vit_solunum"),
        CheckConstraint("ates BETWEEN 25 AND 45", name="ck_vit_ates"),
        CheckConstraint("spo2 BETWEEN 30 AND 100", name="ck_vit_spo2"),
        CheckConstraint("bilinc IN ('A', 'C', 'V', 'P', 'U')", name="ck_vit_bilinc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nabiz: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tansiyon_sistolik: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tansiyon_diyastolik: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    solunum: Mapped[int] = mapped_column(SmallInteger, default=16, nullable=False)
    ates: Mapped[float] = mapped_column(Numeric(4, 1, asdecimal=False), default=36.8, nullable=False)
    spo2: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    troponin: Mapped[float | None] = mapped_column(Numeric(6, 3, asdecimal=False), nullable=True)
    # ACVPU consciousness level and supplemental oxygen, both used by NEWS2
    bilinc: Mapped[str] = mapped_column(String(1), default="A", server_default="A", nullable=False)
    ek_oksijen: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    loglar: Mapped[list["HastaneLog"]] = relationship("HastaneLog", back_populates="vitaller", cascade="all, delete-orphan")


class Sikayet(Base):
    """Card 4: Patient complaint."""
    __tablename__ = "hasta_sikayet"
    __table_args__ = (CheckConstraint("agri_skalasi BETWEEN 1 AND 10", name="ck_sikayet_agri"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ana_sikayet: Mapped[str] = mapped_column(Text, nullable=False)
    agri_skalasi: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    loglar: Mapped[list["HastaneLog"]] = relationship("HastaneLog", back_populates="sikayet", cascade="all, delete-orphan")


class HastaneLog(Base):
    """Master hospital log linking the four cards and storing the AI decision."""
    __tablename__ = "hastane_log"
    __table_args__ = (
        UniqueConstraint("tarih", "sira_no", name="uq_log_tarih_sira"),
        # Daily queue: WHERE tarih = ? ORDER BY risk_skoru, sira_no
        Index("ix_log_kuyruk", "tarih", "risk_skoru", "sira_no"),
        # History: ORDER BY tarih DESC, saat DESC, sira_no DESC (read backwards)
        Index("ix_log_gecmis", "tarih", "saat", "sira_no"),
        CheckConstraint("risk_skoru BETWEEN 1 AND 5", name="ck_log_risk"),
        CheckConstraint("durum IN ('KIRMIZI', 'SARI', 'YESIL')", name="ck_log_durum"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sira_no: Mapped[int] = mapped_column(Integer, nullable=False)
    tarih: Mapped[date] = mapped_column(Date, nullable=False)
    saat: Mapped[time] = mapped_column(Time, nullable=False)

    demografi_id: Mapped[int] = mapped_column(ForeignKey("hasta_demografi.id", ondelete="CASCADE"), nullable=False)
    tibbi_gecmis_id: Mapped[int] = mapped_column(ForeignKey("tibbi_gecmis.id", ondelete="CASCADE"), nullable=False)
    vitaller_id: Mapped[int] = mapped_column(ForeignKey("anlik_vitaller.id", ondelete="CASCADE"), nullable=False)
    sikayet_id: Mapped[int] = mapped_column(ForeignKey("hasta_sikayet.id", ondelete="CASCADE"), nullable=False)

    durum: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_skoru: Mapped[int] = mapped_column(SmallInteger, default=3, nullable=False)
    onerilen_poliklinik: Mapped[str | None] = mapped_column(String(150), nullable=True)
    birim_uyumluluk_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    kritik_bulgu: Mapped[str | None] = mapped_column(String(1500), nullable=True)
    erken_uyari_notu: Mapped[str | None] = mapped_column(String(1500), nullable=True)
    aciklama: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    karar_kaynagi: Mapped[str] = mapped_column(String(50), default="LLM", nullable=False)
    news2_skoru: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)

    islendi: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    demografi: Mapped[HastaDemografi] = relationship("HastaDemografi", back_populates="loglar", lazy="joined")
    tibbi_gecmis: Mapped[TibbiGecmis] = relationship("TibbiGecmis", back_populates="loglar", lazy="joined")
    vitaller: Mapped[AnlikVitaller] = relationship("AnlikVitaller", back_populates="loglar", lazy="joined")
    sikayet: Mapped[Sikayet] = relationship("Sikayet", back_populates="loglar", lazy="joined")


class HastalikSevk(Base):
    """ML training and clinical referral reference table."""
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
    varsayilan_triaj_kodu: Mapped[str] = mapped_column(String(20), nullable=False)
    aciklama: Mapped[str | None] = mapped_column(String(1000), nullable=True)
