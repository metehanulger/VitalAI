from datetime import date
from typing import get_args

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.config import yerel_simdi
from app.core.triage import triaj_karari_ver
from app.db import crud
from app.db.database import get_db
from app.models.schemas import (
    Durum,
    DurumGuncelle,
    KanGrubu,
    KimlikTuru,
    KuyrukOgesi,
    TriajDetay,
    TriajIstek,
    TriajSonuc,
)

router = APIRouter(prefix="/api/triage", tags=["triage"])


def _mask_full_name(name: str) -> str:
    return " ".join(f"{part[0]}{'*' * (len(part) - 1)}" for part in name.split() if part)


@router.post("", response_model=TriajSonuc, status_code=201)
def triaj_olustur(istek: TriajIstek, db: Session = Depends(get_db)):
    """Accept the four triage cards, determine urgency, and save the record."""
    referanslar = crud.ml_egitim_veri_setini_getir(db, limit=500)
    karar = triaj_karari_ver(istek, referanslar)
    return crud.triaj_kaydi_olustur(db, istek, karar, yerel_simdi())


@router.get("", response_model=list[KuyrukOgesi])
def kuyruk(
    tarih: date | None = Query(default=None, description="Defaults to today"),
    durum: Durum | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List today's cases by urgency, then by queue number."""
    kayitlar = crud.kuyruk_getir(db, tarih or yerel_simdi().date(), durum.value if durum else None, limit)
    return [
        KuyrukOgesi(
            log_id=k.id,
            sira_no=k.sira_no,
            tarih=k.tarih,
            saat=k.saat,
            hasta_durumu=k.durum,
            risk_skoru=k.risk_skoru,
            onerilen_poliklinik=k.onerilen_poliklinik,
            isim=_mask_full_name(k.demografi.isim),
            yas=k.demografi.yas,
            ana_sikayet=k.sikayet.ana_sikayet,
            agri_skalasi=k.sikayet.agri_skalasi,
        )
        for k in kayitlar
    ]


@router.get("/secenekler")
def secenekler():
    """Return options and limits used by the intake form."""
    return {
        "kan_gruplari": list(get_args(KanGrubu)),
        "kimlik_turleri": [k.value for k in KimlikTuru],
        "hasta_durumlari": [d.value for d in Durum],
        "agri_skalasi": {"min": 1, "max": 10},
    }


@router.get("/history", response_model=list[TriajDetay])
def tum_kayitlar(
    response: Response,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Return one page of saved triage records, newest first, with their intake cards.

    The total number of records is returned in the X-Total-Count header.
    """
    response.headers["X-Total-Count"] = str(crud.triaj_kayit_sayisi(db))
    return crud.tum_triaj_kayitlarini_getir(db, limit=limit, offset=offset)


def _log_bul(log_id: int, db: Session):
    log = crud.log_detay_getir(db, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Triage record not found")
    return log


@router.get("/{log_id}", response_model=TriajDetay)
def triaj_detay(log_id: int, db: Session = Depends(get_db)):
    """Return the record and all four cards for the result or staff view."""
    return _log_bul(log_id, db)


@router.patch("/{log_id}", response_model=TriajDetay)
def triaj_durum_guncelle(log_id: int, guncelleme: DurumGuncelle, db: Session = Depends(get_db)):
    """Allow staff to manually update the triage status."""
    log = _log_bul(log_id, db)
    return crud.durum_guncelle(db, log, guncelleme.hasta_durumu.value, guncelleme.aciklama)
