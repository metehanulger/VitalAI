"""LLM client behavior that does not need network access."""

from types import SimpleNamespace

import importlib

# app.core re-exports the client instance as "llm_client", so import the module itself.
modul = importlib.import_module("app.core.llm_client")
from app.core.llm_client import UniversalLLMClient


class _SahteModeller:
    def __init__(self):
        self.cagrilar = []

    def generate_content(self, **kwargs):
        self.cagrilar.append(kwargs)
        return SimpleNamespace(text='{"durum": "SARI", "risk_skoru": 3}')


def test_gemini_istemcisi_tekrar_kullanilir_ve_zaman_asimi_iletilir(monkeypatch):
    monkeypatch.setattr(modul.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(modul.settings, "LLM_API_KEY", "")
    istemci = UniversalLLMClient()
    modeller = _SahteModeller()
    istemci._gemini_client = SimpleNamespace(models=modeller)

    assert istemci.provider == "gemini"
    assert istemci.generate("hasta", "sistem", timeout=15) == {"durum": "SARI", "risk_skoru": 3}
    istemci.generate("hasta", "sistem")

    ilk, ikinci = (c["config"] for c in modeller.cagrilar)
    assert ilk.system_instruction == "sistem"
    assert ilk.response_mime_type == "application/json"
    assert ilk.http_options.timeout == 15_000
    assert ikinci.http_options.timeout == int(modul.settings.GEMINI_TIMEOUT_SECONDS * 1000)


def test_json_olmayan_veya_liste_yanit_reddedilir():
    assert UniversalLLMClient._extract_json("açıklama {\"a\": 1} son") == {"a": 1}
    assert UniversalLLMClient._extract_json("[1, 2]") is None
    assert UniversalLLMClient._extract_json("yanıt yok") is None


def test_anahtar_yoksa_istek_gonderilmez(monkeypatch):
    monkeypatch.setattr(modul.settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(modul.settings, "WATSONX_API_KEY", "")
    istemci = UniversalLLMClient(api_key="", base_url=modul.DEFAULT_OPENAI_BASE_URL, provider="openai_compatible")
    monkeypatch.setattr(istemci, "_call_openai_compatible", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert istemci.generate("hasta") is None
