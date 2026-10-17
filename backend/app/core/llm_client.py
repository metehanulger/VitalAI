"""Evrensel LLM İstemcisi (Universal LLM Client).

Bu modül, acil servis triaj değerlendirmesi için herhangi bir LLM sağlayıcısına bağlanabilir:
- OpenAI Uyumlu Sağlayıcılar (OpenAI, DeepSeek, Groq, OpenRouter, Mistral, Together AI, Perplexity)
- Yerel Açık Kaynak Modeller (Ollama, vLLM, LM Studio)
- Google Gemini API (gemini-1.5-flash, gemini-2.0-flash vb.)
- IBM watsonx.ai (Granite, Llama modelleri)

API anahtarı ve model bilgileri ortam değişkenlerinden (.env) veya doğrudan parametre olarak okunur.
"""

import json
import logging
import os
import re
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

from app.core.config import settings
try:
    from app.core import api_config
except ImportError:
    api_config = None

logger = logging.getLogger(__name__)


class UniversalLLMClient:
    """Herhangi bir LLM API'sine bağlanabilen esnek adaptör sınıfı."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        # 1. API Anahtarı (Boş bırakılabilir; api_config.py veya .env üzerinden okunabilir)
        self.api_key = (
            api_key
            or getattr(settings, "LLM_API_KEY", "")
            or (getattr(api_config, "CUSTOM_LLM_API_KEY", "") if api_config else "")
            or os.getenv("LLM_API_KEY", "")
        )

        # 2. Base URL (Varsayılan: OpenAI uyumlu uç nokta veya DeepSeek, Groq, Ollama vb.)
        self.base_url = (
            base_url
            or getattr(settings, "LLM_BASE_URL", "")
            or (getattr(api_config, "CUSTOM_LLM_BASE_URL", "") if api_config else "")
            or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")

        # 3. Model Adı
        self.model = (
            model
            or getattr(settings, "LLM_MODEL", "")
            or (getattr(api_config, "CUSTOM_LLM_MODEL", "") if api_config else "")
            or os.getenv("LLM_MODEL", "gpt-4o-mini")
        )

        # 4. Sağlayıcı Türü ('openai_compatible', 'gemini', 'watsonx', 'ollama')
        self.provider = (
            provider
            or getattr(settings, "LLM_PROVIDER", "")
            or os.getenv("LLM_PROVIDER", "openai_compatible")
        ).lower()

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Verilen promptu yapılandırılmış LLM'e gönderir ve JSON yanıtını döndürür."""
        # 1. Google Gemini seçilmişse veya sadece Gemini anahtarı varsa
        gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if self.provider == "gemini" or (not self.api_key and gemini_key):
            res = self._call_gemini(prompt, system_prompt)
            if res:
                return res

        # 2. IBM watsonx seçilmişse
        watsonx_key = getattr(settings, "WATSONX_API_KEY", "") or os.getenv("WATSONX_API_KEY", "")
        if self.provider == "watsonx" or (not self.api_key and watsonx_key):
            res = self._call_watsonx(prompt, system_prompt)
            if res:
                return res

        # 3. Herhangi bir OpenAI Uyumlu API (DeepSeek, Groq, OpenAI, Ollama, OpenRouter vb.)
        return self._call_openai_compatible(prompt, system_prompt)

    def _call_openai_compatible(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """OpenAI uyumlu standart REST API çağrısı (httpx/urllib ile hafif ve bağımlılıksız)."""
        endpoint = f"{self.base_url}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"} if "ollama" not in self.base_url else None
        }
        # Ollama veya bazı sağlayıcılar response_format desteklemezse None olanı çıkart
        if payload["response_format"] is None:
            del payload["response_format"]

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                body = response.read().decode("utf-8")
                res_data = json.loads(body)
                content = res_data["choices"][0]["message"]["content"]
                return self._extract_json(content)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            logger.warning(f"LLM API Hatası ({e.code}): {error_body}")
        except Exception as e:
            logger.warning(f"LLM API bağlantı hatası: {e}")

        return None

    def _call_gemini(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Google Gemini API çağrısı."""
        gemini_key = (
            getattr(settings, "GEMINI_API_KEY", "")
            or (getattr(api_config, "GEMINI_API_KEY", "") if api_config else "")
            or os.getenv("GEMINI_API_KEY", "")
        )
        if not gemini_key:
            return None

        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model_name = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
            model = genai.GenerativeModel(model_name)

            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = model.generate_content(full_prompt)
            return self._extract_json(response.text)
        except Exception as e:
            logger.warning(f"Gemini çağrı hatası: {e}")
            return None

    def _call_watsonx(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """IBM watsonx.ai çağrısı."""
        url = (
            getattr(settings, "WATSONX_URL", "")
            or (getattr(api_config, "WATSONX_URL", "") if api_config else "")
            or os.getenv("WATSONX_URL", "")
        )
        api_key = (
            getattr(settings, "WATSONX_API_KEY", "")
            or (getattr(api_config, "WATSONX_API_KEY", "") if api_config else "")
            or os.getenv("WATSONX_API_KEY", "")
        )
        project_id = (
            getattr(settings, "WATSONX_PROJECT_ID", "")
            or (getattr(api_config, "WATSONX_PROJECT_ID", "") if api_config else "")
            or os.getenv("WATSONX_PROJECT_ID", "")
        )

        if not url or not api_key or not project_id:
            return None

        try:
            from ibm_watsonx_ai import Credentials
            from ibm_watsonx_ai.foundation_models import ModelInference
            creds = Credentials(url=url, api_key=api_key)
            model = ModelInference(
                model_id=getattr(settings, "WATSONX_MODEL_ID", "ibm/granite-13b-chat-v2"),
                credentials=creds,
                project_id=project_id,
            )
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = model.generate_text(prompt=full_prompt)
            return self._extract_json(response)
        except Exception as e:
            logger.warning(f"watsonx çağrı hatası: {e}")
            return None

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """LLM çıktısından JSON bloğunu güvenle ayrıştırır."""
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Regex ile ilk ve son süslü parantez arasını yakala
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return None


# Global evrensel istemci örneği
llm_client = UniversalLLMClient()
