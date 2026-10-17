from datetime import date
from typing import get_args

from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.post("", response_model=TriajSonuc, status_code=201)
def triaj_olustur(istek: TriajIstek, db: Session = Depends(get_db)):
    """Triaj ekranındaki 4 kartı alır, hasta durumunu belirler, kartları ve log kaydını yazar."""
    # Yapay zekâ çağrısı DB transaction'ı açılmadan önce yapılır
    karar = triaj_karari_ver(istek)
    return crud.triaj_kaydi_olustur(db, istek, karar, yerel_simdi())


@router.get("", response_model=list[KuyrukOgesi])
def kuyruk(
    tarih: date | None = Query(default=None, description="Varsayılan: bugün"),
    durum: Durum | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Günün başvuruları: önce KIRMIZI, sonra SARI, YESIL; her grupta sıra no'ya göre."""
    kayitlar = crud.kuyruk_listele(db, tarih or yerel_simdi().date(), durum.value if durum else None, limit)
    return [
        KuyrukOgesi(
            log_id=k.id,
            sira_no=k.sira_no,
            tarih=k.tarih,
            saat=k.saat,
            hasta_durumu=k.hasta_durumu,
            isim=k.demografi.isim,
            yas=k.demografi.yas,
            ana_sikayet=k.sikayet.ana_sikayet,
            agri_skalasi=k.sikayet.agri_skalasi,
        )
        for k in kayitlar
    ]


@router.get("/secenekler")
def secenekler():
    """Formdaki açılır listeler ve kaydırıcı için sabit değerler."""
    return {
        "kan_gruplari": list(get_args(KanGrubu)),
        "kimlik_turleri": [k.value for k in KimlikTuru],
        "hasta_durumlari": [d.value for d in Durum],
        "agri_skalasi": {"min": 1, "max": 10},
    }


def _log_bul(log_id: int, db: Session):
    log = crud.triaj_getir(db, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Triaj kaydı bulunamadı")
    return log


@router.get("/{log_id}", response_model=TriajDetay)
def triaj_detay(log_id: int, db: Session = Depends(get_db)):
    """Sonuç ekranı / personel görünümü için kayıt ve 4 kartın tamamı (kimlik no maskeli)."""
    return _log_bul(log_id, db)


@router.patch("/{log_id}", response_model=TriajDetay)
def triaj_durum_guncelle(log_id: int, guncelleme: DurumGuncelle, db: Session = Depends(get_db)):
    """Sağlık personeli hasta durumunu elle değiştirir (karar_kaynagi = MANUEL)."""
    log = _log_bul(log_id, db)
    return crud.durum_guncelle(db, log, guncelleme.hasta_durumu.value, guncelleme.aciklama)
