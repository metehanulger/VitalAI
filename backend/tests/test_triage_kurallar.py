from app.core.triage import hasta_ozeti, kural_degerlendir
from app.core.watsonx import yanit_coz
from app.models.schemas import TriajIstek


def _istek(istek, **vitaller):
    istek["vitaller"].update(vitaller)
    return TriajIstek.model_validate(istek)


def test_normal_vitaller_yesil(istek):
    sonuc = kural_degerlendir(TriajIstek.model_validate(istek))
    assert (sonuc.durum, sonuc.news2) == ("YESIL", 0)


def test_news2_yuksek_kirmizi(istek):
    # solunum 25 (3) + nabız 125 (2) + ateş 39.5 (2) = 7
    sonuc = kural_degerlendir(_istek(istek, solunum=25, nabiz=125, ates=39.5))
    assert sonuc.news2 == 7
    assert sonuc.durum == "KIRMIZI"


def test_kelime_basi_eslesme(istek):
    istek["sikayet"]["ana_sikayet"] = "Dinmeyen baş ağrısı"
    assert kural_degerlendir(TriajIstek.model_validate(istek)).durum == "YESIL"
    istek["sikayet"]["ana_sikayet"] = "Babam İNME geçirdi galiba"
    assert kural_degerlendir(TriajIstek.model_validate(istek)).durum == "KIRMIZI"


def test_ozet_kisisel_veri_icermez(istek):
    ozet = hasta_ozeti(TriajIstek.model_validate(istek), kural_degerlendir(TriajIstek.model_validate(istek)))
    assert "Ayşe" not in ozet and "10000000146" not in ozet
    assert "SpO2 %98" in ozet


def test_yanit_coz():
    assert yanit_coz('Sonuç:\n```json\n{"durum": "YEŞİL", "aciklama": "Stabil."}\n```') == ("YESIL", "Stabil.")
    assert yanit_coz('{"durum": "MAVI"}') is None
    assert yanit_coz("JSON yok") is None
