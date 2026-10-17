"""Triaj kararı: kural tabanlı değerlendirme + watsonx.ai.

Kural motoru vitallerden NEWS2 skorunu hesaplar ve kritik eşikleri/anahtar kelimeleri arar.
Son karar ikisinden DAHA ACİL olandır; yapay zekâ kural sonucunu yalnızca yükseltebilir,
düşüremez. Böylece model hatası veya şikayet metnine gömülü talimatlar hastayı geriye atamaz.
NEWS2 erişkinler için tasarlanmıştır; çocuklarda eşikler fazla temkinli (üst triaj) kalabilir.
"""

import re
from dataclasses import dataclass, field

from app.core import watsonx
from app.core.metin import katla
from app.models.schemas import TriajIstek, VitallerIn

SEVIYELER = ("YESIL", "SARI", "KIRMIZI")  # artan aciliyet

KRITIK_KELIMELER = [
    "bilinc kaybi", "bilinci kapali", "bayildi ve uyanmiyor", "nefes alamiyor", "nefes alamiyorum",
    "solunum durmasi", "kalp durmasi", "gogus agrisi", "gogsumde agri", "felc", "inme",
    "konusamiyor", "nobet", "havale", "siddetli kanama", "intihar", "zehirlen", "anafilaksi",
]
ACIL_KELIMELER = [
    "nefes darligi", "kanama", "kirik", "bayil", "carpinti", "kusma", "karin agrisi",
    "yuksek ates", "hamile", "gebe", "yanik", "kafa travmasi", "basini carpti",
]


def _ilk_eslesen(kelimeler: list[str], metin: str) -> str | None:
    # Kelime başında eşleşme: "inme" -> "inme geçirdi" evet, "dinmeyen" hayır
    return next((k for k in kelimeler if re.search(r"\b" + re.escape(k), metin)), None)


def _seviye(durum: str) -> int:
    return SEVIYELER.index(durum)


def _en_acil(*durumlar: str) -> str:
    return max(durumlar, key=_seviye)


def news2_skoru(v: VitallerIn) -> tuple[int, list[str]]:
    """NEWS2 toplamı ve tek başına 3 puan alan parametreler (bilinç ve O2 desteği formda yok)."""
    puanlar = {
        "Solunum": 3 if v.solunum <= 8 else 1 if v.solunum <= 11 else 0 if v.solunum <= 20 else 2 if v.solunum <= 24 else 3,
        "SpO2": 3 if v.spo2 <= 91 else 2 if v.spo2 <= 93 else 1 if v.spo2 <= 95 else 0,
        "Sistolik": 3 if v.tansiyon_sistolik <= 90 else 2 if v.tansiyon_sistolik <= 100 else 1 if v.tansiyon_sistolik <= 110 else 0 if v.tansiyon_sistolik <= 219 else 3,
        "Nabız": 3 if v.nabiz <= 40 else 1 if v.nabiz <= 50 else 0 if v.nabiz <= 90 else 1 if v.nabiz <= 110 else 2 if v.nabiz <= 130 else 3,
        "Ateş": 3 if v.ates <= 35.0 else 1 if v.ates <= 36.0 else 0 if v.ates <= 38.0 else 1 if v.ates <= 39.0 else 2,
    }
    return sum(puanlar.values()), [ad for ad, p in puanlar.items() if p == 3]


@dataclass
class KuralSonucu:
    durum: str
    news2: int
    bulgular: list[str] = field(default_factory=list)

    @property
    def aciklama(self) -> str:
        if not self.bulgular:
            return f"Kural tabanlı değerlendirmede kritik bulgu yok (NEWS2={self.news2})."
        return "; ".join(self.bulgular)


def kural_degerlendir(istek: TriajIstek) -> KuralSonucu:
    v, s = istek.vitaller, istek.sikayet
    news2, uc_puanlilar = news2_skoru(v)
    durum, bulgular = "YESIL", []

    def yukselt(yeni: str, neden: str) -> None:
        nonlocal durum
        durum = _en_acil(durum, yeni)
        bulgular.append(neden)

    if news2 >= 7:
        yukselt("KIRMIZI", f"NEWS2 skoru {news2} (yüksek risk)")
    elif news2 >= 5:
        yukselt("SARI", f"NEWS2 skoru {news2} (orta risk)")
    if uc_puanlilar:
        yukselt("SARI", "Tek parametrede ağır sapma: " + ", ".join(uc_puanlilar))

    # Tek başına hayati tehlike gösteren eşikler
    if v.spo2 < 90:
        yukselt("KIRMIZI", f"SpO2 %{v.spo2}")
    if v.tansiyon_sistolik < 90:
        yukselt("KIRMIZI", f"Hipotansiyon ({v.tansiyon_sistolik}/{v.tansiyon_diastolik} mmHg)")
    if v.tansiyon_sistolik >= 220 or v.tansiyon_diastolik >= 130:
        yukselt("KIRMIZI", f"Hipertansif acil ({v.tansiyon_sistolik}/{v.tansiyon_diastolik} mmHg)")
    if v.nabiz < 40 or v.nabiz > 150:
        yukselt("KIRMIZI", f"Nabız {v.nabiz}/dk")
    if v.solunum < 8 or v.solunum > 30:
        yukselt("KIRMIZI", f"Solunum {v.solunum}/dk")
    if v.ates >= 41 or v.ates < 35:
        yukselt("KIRMIZI", f"Ateş {v.ates} °C")

    metin = katla(s.ana_sikayet)
    if kelime := _ilk_eslesen(KRITIK_KELIMELER, metin):
        yukselt("KIRMIZI", f"Şikayette kritik ifade: '{kelime}'")
    elif kelime := _ilk_eslesen(ACIL_KELIMELER, metin):
        yukselt("SARI", f"Şikayette acil ifade: '{kelime}'")

    if s.agri_skalasi >= 8:
        yukselt("SARI", f"Şiddetli ağrı ({s.agri_skalasi}/10)")

    return KuralSonucu(durum=durum, news2=news2, bulgular=bulgular)


def hasta_ozeti(istek: TriajIstek, kural: KuralSonucu) -> str:
    """Modele gönderilen özet. İsim ve kimlik no gibi kişisel veriler gönderilmez."""
    d, t, v, s = istek.demografi, istek.tibbi_gecmis, istek.vitaller, istek.sikayet
    return "\n".join([
        f"Yaş: {d.yas}",
        f"Boy/Kilo: {d.boy or '?'} cm / {d.kilo or '?'} kg",
        f"Kan grubu: {d.kan_grubu}",
        f"Kronik rahatsızlık: {t.kronik_rahatsizlik or 'yok'}",
        f"Sürekli ilaç: {t.surekli_ilac or 'yok'}",
        f"Vitaller: Nabız {v.nabiz}/dk, Tansiyon {v.tansiyon_sistolik}/{v.tansiyon_diastolik} mmHg, "
        f"Solunum {v.solunum}/dk, Ateş {v.ates} °C, SpO2 %{v.spo2}",
        f"Ana şikayet: {s.ana_sikayet}",
        f"Ağrı skalası: {s.agri_skalasi}/10",
        f"Kural tabanlı ön değerlendirme: {kural.durum} ({kural.aciklama})",
    ])


@dataclass
class TriajKarari:
    durum: str
    aciklama: str
    kaynak: str  # KURAL | WATSONX | KURAL+WATSONX


def triaj_karari_ver(istek: TriajIstek) -> TriajKarari:
    kural = kural_degerlendir(istek)
    yz = watsonx.degerlendir(hasta_ozeti(istek, kural))
    if yz is None:
        return TriajKarari(kural.durum, kural.aciklama, "KURAL")

    yz_durum, yz_aciklama = yz
    if _seviye(yz_durum) > _seviye(kural.durum):
        kaynak = "WATSONX"
    elif _seviye(yz_durum) < _seviye(kural.durum):
        kaynak = "KURAL"
    else:
        kaynak = "KURAL+WATSONX"
    aciklama = f"{yz_aciklama} | Kural: {kural.aciklama}" if yz_aciklama else kural.aciklama
    return TriajKarari(_en_acil(kural.durum, yz_durum), aciklama, kaynak)
