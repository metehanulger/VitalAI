"""JSON contract between the frontend and backend.

The frontend sends all four cards in one request (POST /api/triage):
    {"demografi": {...}, "tibbi_gecmis": {...}, "vitaller": {...}, "sikayet": {...}}
"""

import re
from datetime import date, time
from enum import Enum
from typing import Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.core.metin import katla


class Durum(str, Enum):
    """Patient triage status using the standard color categories."""

    KIRMIZI = "KIRMIZI"
    SARI = "SARI"
    YESIL = "YESIL"


class KimlikTuru(str, Enum):
    TC = "TC"
    PASAPORT = "PASAPORT"


KanGrubu = Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "0+", "0-", "BILINMIYOR"]
KararKaynagi = str


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


class DemografiIn(_Girdi):
    isim: str = Field(min_length=2, max_length=100)
    yas: int = Field(ge=0, le=130)
    boy: int | None = Field(default=None, ge=20, le=260, description="cm")
    kilo: float | None = Field(default=None, ge=0.5, le=400, description="kg")
    kan_grubu: KanGrubu = "BILINMIYOR"
    kimlik_turu: KimlikTuru
    kimlik_no: str = Field(description="Turkish ID number (11 digits) or passport number")

    @field_validator("kimlik_turu", mode="before")
    @classmethod
    def _kimlik_turu_normalize(cls, value):
        if isinstance(value, KimlikTuru):
            return value.value
        if isinstance(value, str) and value.startswith("KimlikTuru."):
            return value.rsplit(".", 1)[-1]
        return value

    @field_validator("kan_grubu", mode="before")
    @classmethod
    def _kan_grubu_normalize(cls, v):
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
                raise ValueError("Invalid Turkish ID number")
        elif not re.fullmatch(r"[A-Z0-9]{5,20}", no):
            raise ValueError("Passport number must contain 5-20 letters or digits")
        self.kimlik_no = no
        return self


class TibbiGecmisIn(_Girdi):
    kronik_rahatsizlik: str | None = Field(default=None, max_length=400)
    surekli_ilac: str | None = Field(default=None, max_length=400)

    @field_validator("kronik_rahatsizlik", "surekli_ilac")
    @classmethod
    def _bos_ise_none(cls, v):
        return v or None


class VitallerIn(_Girdi):
    nabiz: int = Field(ge=20, le=300, description="beats/min")
    tansiyon_sistolik: int = Field(ge=40, le=300, description="mmHg")
    tansiyon_diastolik: int = Field(
        ge=20,
        le=200,
        description="mmHg",
        validation_alias=AliasChoices("tansiyon_diastolik", "tansiyon_diyastolik"),
    )
    solunum: int = Field(ge=4, le=80, description="breaths/min")
    ates: float = Field(ge=25, le=45, description="°C")
    spo2: int = Field(ge=30, le=100, description="%")

    @model_validator(mode="after")
    def _tansiyon_kontrol(self):
        if self.tansiyon_sistolik <= self.tansiyon_diastolik:
            raise ValueError("Systolic blood pressure must be greater than diastolic blood pressure")
        return self


class SikayetIn(_Girdi):
    ana_sikayet: str = Field(min_length=2, max_length=800)
    agri_skalasi: int = Field(ge=1, le=10, description="scale from 1 to 10")


class TriajIstek(BaseModel):
    demografi: DemografiIn
    tibbi_gecmis: TibbiGecmisIn = Field(default_factory=TibbiGecmisIn)
    vitaller: VitallerIn
    sikayet: SikayetIn


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
    """IDs of the four cards stored in the hospital log."""

    demografi_id: int
    tibbi_gecmis_id: int
    vitaller_id: int
    sikayet_id: int


class TriajSonuc(BaseModel):
    """POST /api/triage response displayed on the result screen."""

    model_config = ConfigDict(from_attributes=True)

    log_id: int = Field(validation_alias=AliasChoices("log_id", "id"))
    sira_no: int
    tarih: date
    saat: time
    hasta_durumu: Durum
    risk_skoru: int = Field(ge=1, le=5, description="ESI level: 1 is most urgent and 5 is least urgent")
    onerilen_poliklinik: str | None = None
    aciklama: str | None
    karar_kaynagi: KararKaynagi
    kodlar: TriajKodlari

    @model_validator(mode="before")
    @classmethod
    def _hastane_logunu_esle(cls, value):
        """Map the SQLAlchemy log row and its card foreign keys to the API response."""
        if isinstance(value, dict) or not hasattr(value, "demografi_id"):
            return value

        return {
            "log_id": value.id,
            "sira_no": value.sira_no,
            "tarih": value.tarih,
            "saat": value.saat,
            "hasta_durumu": value.durum,
            "risk_skoru": value.risk_skoru,
            "onerilen_poliklinik": value.onerilen_poliklinik,
            "aciklama": value.aciklama,
            "karar_kaynagi": value.karar_kaynagi,
            "kodlar": {
                "demografi_id": value.demografi_id,
                "tibbi_gecmis_id": value.tibbi_gecmis_id,
                "vitaller_id": value.vitaller_id,
                "sikayet_id": value.sikayet_id,
            },
            "demografi": value.demografi,
            "tibbi_gecmis": value.tibbi_gecmis,
            "vitaller": value.vitaller,
            "sikayet": value.sikayet,
        }

    @computed_field
    @property
    def aciliyet_seviyesi(self) -> int:
        """Project scale: 1 is not urgent and 5 is very urgent."""
        return 6 - self.risk_skoru


class TriajDetay(TriajSonuc):
    demografi: DemografiOut
    tibbi_gecmis: TibbiGecmisOut
    vitaller: VitallerOut
    sikayet: SikayetOut


class KuyrukOgesi(BaseModel):
    """Queue entry ordered by urgency and then queue number."""

    log_id: int
    sira_no: int
    tarih: date
    saat: time
    hasta_durumu: Durum
    risk_skoru: int = Field(ge=1, le=5)
    onerilen_poliklinik: str | None = None
    isim: str
    yas: int
    ana_sikayet: str
    agri_skalasi: int

    @computed_field
    @property
    def aciliyet_seviyesi(self) -> int:
        return 6 - self.risk_skoru


class DurumGuncelle(_Girdi):
    """Manual triage status update submitted by a staff member."""

    hasta_durumu: Durum
    aciklama: str | None = Field(default=None, max_length=500)
