"""Frontend ile backend arasındaki JSON sözleşmesi.

Frontend 4 kartı tek istekte gönderir (POST /api/triage):
    {"demografi": {...}, "tibbi_gecmis": {...}, "vitaller": {...}, "sikayet": {...}}
"""

import re
from datetime import date, time
from enum import Enum
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.core.metin import katla


class Durum(str, Enum):
    """Hasta durumu: Sağlık Bakanlığı renk kodlu triaj."""

    KIRMIZI = "KIRMIZI"
    SARI = "SARI"
    YESIL = "YESIL"


class KimlikTuru(str, Enum):
    TC = "TC"
    PASAPORT = "PASAPORT"


KanGrubu = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "0+", "0-", "BILINMIYOR"]
KararKaynagi = Literal["KURAL", "WATSONX", "KURAL+WATSONX", "MANUEL"]


class _Girdi(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


def tc_kimlik_gecerli_mi(no: str) -> bool:
    if not re.fullmatch(r"[1-9]\d{10}", no):
        return False
    d = [int(c) for c in no]
    tek, cift = sum(d[0:9:2]), sum(d[1:8:2])
    return (tek * 7 - cift) % 10 == d[9] and sum(d[:10]) % 10 == d[10]


def kimlik_maskele(no: str) -> str:
    if len(no) <= 6:
        return "*" * len(no)
    return no[:2] + "*" * (len(no) - 4) + no[-2:]


# --- Kart 1: Temel Demografi ---
class DemografiIn(_Girdi):
    isim: str = Field(min_length=2, max_length=100)
    yas: int = Field(ge=0, le=130)
    boy: int | None = Field(default=None, ge=20, le=260, description="cm")
    kilo: float | None = Field(default=None, ge=0.5, le=400, description="kg")
    kan_grubu: KanGrubu = "BILINMIYOR"
    kimlik_turu: KimlikTuru
    kimlik_no: str = Field(description="TC kimlik no (11 hane) veya pasaport no")

    @field_validator("kan_grubu", mode="before")
    @classmethod
    def _kan_grubu_normalize(cls, v):
        # "O Rh+", "a+", "Bilinmiyor" gibi yazımları kabul et
        if isinstance(v, str):
            v = katla(v).upper().replace(" ", "").replace("RH", "")
            if v in ("", "BILINMIYOR"):
                return "BILINMIYOR"
            return v.replace("O", "0")
        return v

    @model_validator(mode="after")
    def _kimlik_dogrula(self):
        no = self.kimlik_no.replace(" ", "").upper()
        if self.kimlik_turu is KimlikTuru.TC:
            if not tc_kimlik_gecerli_mi(no):
                raise ValueError("Geçersiz TC kimlik numarası")
        elif not re.fullmatch(r"[A-Z0-9]{5,20}", no):
            raise ValueError("Pasaport numarası 5-20 harf/rakam olmalıdır")
        self.kimlik_no = no
        return self


# --- Kart 2: Tıbbi Geçmiş ---
class TibbiGecmisIn(_Girdi):
    kronik_rahatsizlik: str | None = Field(default=None, max_length=400)
    surekli_ilac: str | None = Field(default=None, max_length=400)

    @field_validator("kronik_rahatsizlik", "surekli_ilac")
    @classmethod
    def _bos_ise_none(cls, v):
        return v or None


# --- Kart 3: Anlık Vitaller ---
class VitallerIn(_Girdi):
    nabiz: int = Field(ge=20, le=300, description="atım/dk")
    tansiyon_sistolik: int = Field(ge=40, le=300, description="mmHg")
    tansiyon_diastolik: int = Field(ge=20, le=200, description="mmHg")
    solunum: int = Field(ge=4, le=80, description="nefes/dk")
    ates: float = Field(ge=25, le=45, description="°C")
    spo2: int = Field(ge=30, le=100, description="%")

    @model_validator(mode="after")
    def _tansiyon_kontrol(self):
        if self.tansiyon_sistolik <= self.tansiyon_diastolik:
            raise ValueError("Sistolik tansiyon diastolikten büyük olmalıdır")
        return self


# --- Kart 4: Şikayet ---
class SikayetIn(_Girdi):
    ana_sikayet: str = Field(min_length=2, max_length=800)
    agri_skalasi: int = Field(ge=1, le=10, description="1-10 arası kaydırıcı")


class TriajIstek(BaseModel):
    demografi: DemografiIn
    tibbi_gecmis: TibbiGecmisIn = Field(default_factory=TibbiGecmisIn)
    vitaller: VitallerIn
    sikayet: SikayetIn


# --- Yanıtlar ---
class DemografiOut(DemografiIn):
    model_config = ConfigDict(from_attributes=True)
    id: int

    @field_serializer("kimlik_no")
    def _maskele(self, no: str) -> str:
        return kimlik_maskele(no)


class TibbiGecmisOut(TibbiGecmisIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class VitallerOut(VitallerIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SikayetOut(SikayetIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TriajKodlari(BaseModel):
    """HASTANE_LOG'da tutulan 4 kart kodu."""

    demografi_id: int
    tibbi_gecmis_id: int
    vitaller_id: int
    sikayet_id: int


class TriajSonuc(BaseModel):
    """POST /api/triage yanıtı: Sonuç ekranında gösterilir."""

    model_config = ConfigDict(from_attributes=True)

    log_id: int = Field(validation_alias=AliasChoices("log_id", "id"))
    sira_no: int
    tarih: date
    saat: time
    hasta_durumu: Durum
    aciklama: str | None
    karar_kaynagi: KararKaynagi
    kodlar: TriajKodlari


class TriajDetay(TriajSonuc):
    demografi: DemografiOut
    tibbi_gecmis: TibbiGecmisOut
    vitaller: VitallerOut
    sikayet: SikayetOut


class KuyrukOgesi(BaseModel):
    """Bekleme listesi satırı (aciliyet, sonra sıra no'ya göre sıralı)."""

    log_id: int
    sira_no: int
    tarih: date
    saat: time
    hasta_durumu: Durum
    isim: str
    yas: int
    ana_sikayet: str
    agri_skalasi: int


class DurumGuncelle(_Girdi):
    """Sağlık personelinin triaj sonucunu elle değiştirmesi."""

    hasta_durumu: Durum
    aciklama: str | None = Field(default=None, max_length=500)
