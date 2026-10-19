from app.core.prompts import build_full_triage_prompt
from app.core.triage import kural_tabanli_degerlendir, news2_hesapla
from app.core.llm_client import UniversalLLMClient
from app.models.schemas import TriajIstek


def _istek(istek, **vitaller):
    istek["vitaller"].update(vitaller)
    return TriajIstek.model_validate(istek)


def test_normal_vitaller_yesil(istek):
    istek = TriajIstek.model_validate(istek)
    assert news2_hesapla(istek.vitaller) == (0, [])
    durum, _gerekce, news2 = kural_tabanli_degerlendir(istek)
    assert (durum, news2) == ("YESIL", 0)


def test_news2_yuksek_kirmizi(istek):
    istek = _istek(istek, solunum=25, nabiz=125, ates=39.5)
    durum, _gerekce, news2 = kural_tabanli_degerlendir(istek)
    assert news2 == 7
    assert durum == "KIRMIZI"


def test_kelime_basi_eslesme(istek):
    istek["sikayet"]["ana_sikayet"] = "Dinmeyen baş ağrısı"
    assert kural_tabanli_degerlendir(TriajIstek.model_validate(istek))[0] == "YESIL"
    istek["sikayet"]["ana_sikayet"] = "Babam İNME geçirdi galiba"
    assert kural_tabanli_degerlendir(TriajIstek.model_validate(istek))[0] == "KIRMIZI"


def test_ozet_kisisel_veri_icermez(istek):
    ozet = build_full_triage_prompt(TriajIstek.model_validate(istek))
    assert "Ayşe" not in ozet and "10000000146" not in ozet
    assert "Oxygen saturation (SpO2): 98%" in ozet


def test_llm_json_extracts():
    assert UniversalLLMClient._extract_json('Yanıt: {"durum": "KIRMIZI"}') == {"durum": "KIRMIZI"}
    assert UniversalLLMClient._extract_json("JSON yok") is None
