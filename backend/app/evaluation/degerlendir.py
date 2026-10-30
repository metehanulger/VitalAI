"""Evaluate the triage engine on labeled cases.

The case file is a CSV with the columns of ``evaluation/vakalar_ornek.csv``. The
expected status and department must come from a nurse or physician; the example
file is only a format sample and its labels are not clinically validated.

Usage from backend/:
    uv run python -m app.evaluation.degerlendir --vakalar evaluation/vakalar_ornek.csv
    uv run python -m app.evaluation.degerlendir --vakalar cases.csv --llm-yok
    uv run python -m app.evaluation.degerlendir --vakalar cases.csv --bekleme 30 --cikti sonuclar.csv

Under-triage (a patient rated less urgent than the label) is reported first
because it is the most dangerous error.
"""

import argparse
import csv
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SEVIYE = {"YESIL": 0, "SARI": 1, "KIRMIZI": 2}
_EVET = {"1", "true", "evet", "yes", "e", "y"}


@dataclass
class VakaSonucu:
    vaka_id: str
    beklenen_durum: str
    tahmin_durum: str
    beklenen_poliklinik: str
    tahmin_poliklinik: str
    ilk_uc_poliklinik: list[str]
    karar_kaynagi: str
    sure_sn: float


def _sayi(deger: str, tip=float):
    deger = (deger or "").strip()
    return tip(deger) if deger else None


def satiri_istege_cevir(satir: dict[str, str]) -> dict[str, Any]:
    """Convert one CSV row into the POST /api/triage request body."""
    return {
        "demografi": {
            "isim": "Degerlendirme Vakasi",
            "yas": _sayi(satir["yas"], int),
            "kimlik_turu": "TC",
            "kimlik_no": "10000000146",
        },
        "tibbi_gecmis": {
            "kronik_rahatsizlik": (satir.get("kronik_rahatsizlik") or "").strip() or None,
            "surekli_ilac": (satir.get("surekli_ilac") or "").strip() or None,
        },
        "vitaller": {
            "nabiz": _sayi(satir["nabiz"], int),
            "tansiyon_sistolik": _sayi(satir["tansiyon_sistolik"], int),
            "tansiyon_diastolik": _sayi(satir["tansiyon_diastolik"], int),
            "solunum": _sayi(satir["solunum"], int),
            "ates": _sayi(satir["ates"]),
            "spo2": _sayi(satir["spo2"], int),
            "bilinc": (satir.get("bilinc") or "A").strip().upper(),
            "ek_oksijen": (satir.get("ek_oksijen") or "").strip().lower() in _EVET,
        },
        "sikayet": {
            "ana_sikayet": satir["ana_sikayet"].strip(),
            "agri_skalasi": _sayi(satir["agri_skalasi"], int),
        },
    }


def metrikler(sonuclar: Iterable[VakaSonucu]) -> dict[str, float]:
    """Return status and department metrics as fractions of the evaluated cases."""
    sonuclar = list(sonuclar)
    n = len(sonuclar)
    if n == 0:
        return {"vaka": 0}
    fark = [SEVIYE[s.tahmin_durum] - SEVIYE[s.beklenen_durum] for s in sonuclar]
    poliklinikli = [s for s in sonuclar if s.beklenen_poliklinik]
    m = len(poliklinikli)
    return {
        "vaka": n,
        "dusuk_triyaj": sum(f < 0 for f in fark) / n,
        "yuksek_triyaj": sum(f > 0 for f in fark) / n,
        "durum_dogrulugu": sum(f == 0 for f in fark) / n,
        "poliklinik_ilk1": sum(s.tahmin_poliklinik == s.beklenen_poliklinik for s in poliklinikli) / m if m else 0.0,
        "poliklinik_ilk3": sum(s.beklenen_poliklinik in s.ilk_uc_poliklinik for s in poliklinikli) / m if m else 0.0,
        "llm_kullanildi": sum("KURAL" != s.karar_kaynagi.split("+")[0] for s in sonuclar) / n,
        "ortalama_sure_sn": sum(s.sure_sn for s in sonuclar) / n,
    }


def _referanslar():
    """Load the referral reference rows from the database, or None when it is unreachable."""
    try:
        from app.db import crud
        from app.db.database import SessionLocal

        with SessionLocal() as db:
            satirlar = crud.ml_egitim_veri_setini_getir(db, limit=500)
            for satir in satirlar:
                db.expunge(satir)
            return satirlar
    except Exception as hata:  # noqa: BLE001 - evaluation still runs without the database
        logging.getLogger(__name__).warning("Reference table unavailable, continuing without it: %s", hata)
        return None


def degerlendir(yol: Path, llm_kullan: bool = True, bekleme: float = 0.0) -> list[VakaSonucu]:
    from app.core import triage
    from app.models.schemas import TriajIstek

    if not llm_kullan:
        triage.llm_client.generate = lambda *a, **k: None
    referanslar = _referanslar()

    sonuclar = []
    with yol.open(encoding="utf-8") as dosya:
        for i, satir in enumerate(csv.DictReader(dosya)):
            if i and bekleme:
                time.sleep(bekleme)
            istek = TriajIstek.model_validate(satiri_istege_cevir(satir))
            baslangic = time.perf_counter()
            karar = triage.triaj_karari_ver(istek, referanslar)
            sure = time.perf_counter() - baslangic
            birimler = [b.birim for b in karar.birim_uyumluluk_siralamasi]
            ilk_uc = list(dict.fromkeys([karar.onerilen_poliklinik, *birimler]))[:3]
            sonuclar.append(VakaSonucu(
                vaka_id=satir.get("vaka_id") or str(i + 1),
                beklenen_durum=satir["beklenen_durum"].strip().upper(),
                tahmin_durum=karar.durum,
                beklenen_poliklinik=(satir.get("beklenen_poliklinik") or "").strip(),
                tahmin_poliklinik=karar.onerilen_poliklinik,
                ilk_uc_poliklinik=ilk_uc,
                karar_kaynagi=karar.karar_kaynagi,
                sure_sn=round(sure, 2),
            ))
    return sonuclar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vakalar", required=True, type=Path, help="CSV file with labeled cases")
    parser.add_argument("--llm-yok", action="store_true", help="Evaluate rules and ML only, without LLM calls")
    parser.add_argument("--bekleme", type=float, default=0.0, help="Seconds to wait between cases (rate limits)")
    parser.add_argument("--cikti", type=Path, help="Optional CSV file for per-case results")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    sonuclar = degerlendir(args.vakalar, llm_kullan=not args.llm_yok, bekleme=args.bekleme)

    for s in sonuclar:
        isaret = "OK " if s.tahmin_durum == s.beklenen_durum else ("LOW" if SEVIYE[s.tahmin_durum] < SEVIYE[s.beklenen_durum] else "HIGH")
        print(f"[{isaret}] {s.vaka_id}: {s.tahmin_durum} (expected {s.beklenen_durum}), "
              f"{s.tahmin_poliklinik} (expected {s.beklenen_poliklinik or '-'}), {s.karar_kaynagi}, {s.sure_sn}s")

    m = metrikler(sonuclar)
    print(f"\nCases: {m['vaka']}")
    if m["vaka"]:
        print(f"Under-triage rate:   {m['dusuk_triyaj']:.1%}")
        print(f"Over-triage rate:    {m['yuksek_triyaj']:.1%}")
        print(f"Status accuracy:     {m['durum_dogrulugu']:.1%}")
        print(f"Department top-1:    {m['poliklinik_ilk1']:.1%}")
        print(f"Department top-3:    {m['poliklinik_ilk3']:.1%}")
        print(f"LLM answered:        {m['llm_kullanildi']:.1%}")
        print(f"Mean time per case:  {m['ortalama_sure_sn']:.1f}s")

    if args.cikti:
        with args.cikti.open("w", encoding="utf-8", newline="") as dosya:
            yazici = csv.writer(dosya)
            yazici.writerow(["vaka_id", "beklenen_durum", "tahmin_durum", "beklenen_poliklinik",
                             "tahmin_poliklinik", "ilk_uc_poliklinik", "karar_kaynagi", "sure_sn"])
            for s in sonuclar:
                yazici.writerow([s.vaka_id, s.beklenen_durum, s.tahmin_durum, s.beklenen_poliklinik,
                                 s.tahmin_poliklinik, " | ".join(s.ilk_uc_poliklinik), s.karar_kaynagi, s.sure_sn])


if __name__ == "__main__":
    main()
