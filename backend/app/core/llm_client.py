"""Universal LLM client.

Supports OpenAI-compatible providers, local models, Google Gemini (google-genai),
and IBM watsonx.ai. All credentials and model names come from app.core.config.
Provider SDK clients are created once and reused across requests.
"""

import json
import logging
import re
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
LLM_TEMPERATURE = 0.1


class UniversalLLMClient:
    """Flexible adapter for connecting to LLM APIs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = (base_url or settings.LLM_BASE_URL or DEFAULT_OPENAI_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL

        configured_provider = (provider or settings.LLM_PROVIDER or "openai_compatible").lower()
        self.provider = (
            "gemini"
            if configured_provider == "openai_compatible" and not self.api_key and settings.GEMINI_API_KEY
            else configured_provider
        )

        self._lock = threading.Lock()
        self._gemini_client = None
        self._watsonx_model = None
        # Set to False after a provider rejects structured output, so later calls skip it.
        self._openai_schema_destegi = True
        self._gemini_schema_destegi = True
        # Gemini model name -> monotonic time until which the model is skipped
        self._model_bekleme: dict[str, float] = {}

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: Optional[float] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Send a prompt to the configured LLM and return its JSON response.

        ``timeout`` (seconds) overrides the provider's default request timeout.
        ``json_schema`` asks providers that support structured output to follow the
        schema; providers that reject it are retried once without it.
        """
        if self.provider == "gemini" or (not self.api_key and settings.GEMINI_API_KEY):
            res = self._call_gemini(prompt, system_prompt, timeout, json_schema)
            if res:
                return res

        if self.provider == "watsonx" or (not self.api_key and settings.WATSONX_API_KEY):
            res = self._call_watsonx(prompt, system_prompt)
            if res:
                return res

        if not self.api_key and self.base_url.lower() == DEFAULT_OPENAI_BASE_URL:
            logger.debug("LLM request skipped: no API key is configured for the default OpenAI endpoint")
            return None

        return self._call_openai_compatible(prompt, system_prompt, timeout, json_schema)

    def _call_openai_compatible(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: Optional[float] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Call a standard OpenAI-compatible REST API using urllib."""
        endpoint = f"{self.base_url}/chat/completions"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": LLM_TEMPERATURE,
        }
        schema_kullan = bool(json_schema) and self._openai_schema_destegi and "ollama" not in self.base_url
        if schema_kullan:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "strict": True, "schema": json_schema},
            }
        elif "ollama" not in self.base_url:
            payload["response_format"] = {"type": "json_object"}

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            req = urllib.request.Request(
                endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout or settings.LLM_TIMEOUT_SECONDS) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data["choices"][0]["message"]["content"]
                return self._extract_json(content)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            if schema_kullan and e.code in (400, 422):
                logger.info("Provider rejected structured output; falling back to JSON mode")
                self._openai_schema_destegi = False
                return self._call_openai_compatible(prompt, system_prompt, timeout)
            logger.warning("LLM API error (%s): %s", e.code, error_body)
        except Exception as e:
            logger.warning("LLM API connection error: %s", e)
        return None

    def _gemini(self):
        """Return the shared google-genai client, creating it on first use."""
        if self._gemini_client is None:
            with self._lock:
                if self._gemini_client is None:
                    from google import genai

                    self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return self._gemini_client

    def _gemini_modelleri(self) -> list[str]:
        """Primary Gemini model followed by the configured fallbacks, without duplicates."""
        adlar = [settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS.split(",")]
        return list(dict.fromkeys(ad.strip() for ad in adlar if ad and ad.strip()))

    def _beklemede(self, model: str) -> bool:
        with self._lock:
            return self._model_bekleme.get(model, 0.0) > time.monotonic()

    def _beklemeye_al(self, model: str, hata: Exception) -> None:
        """Skip a failing model for a while so later requests go straight to a fallback.

        Quota errors wait a minute (or an hour for daily quotas), unknown or forbidden
        models an hour, and timeouts or server errors two minutes.
        """
        kod = getattr(hata, "code", None)
        metin = str(hata).lower()
        if kod == 429:
            sure = 3600 if "per day" in metin else 60
        elif kod in (403, 404):
            sure = 3600
        elif (isinstance(kod, int) and kod >= 500) or "timeout" in type(hata).__name__.lower() or "deadline" in metin:
            sure = 120
        else:
            sure = 30
        with self._lock:
            self._model_bekleme[model] = time.monotonic() + sure
        logger.warning("Gemini model %s failed (%s); skipping it for %ss: %s", model, kod, sure, hata)

    def _call_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout: Optional[float] = None,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Call Gemini, trying fallback models when the current one fails.

        The whole call is capped at 1.5 times the timeout, so a slow primary model
        still leaves time for one fallback without letting the request run on.
        """
        if not settings.GEMINI_API_KEY:
            return None

        sure = timeout or settings.GEMINI_TIMEOUT_SECONDS
        son_an = time.monotonic() + sure * 1.5
        for model in self._gemini_modelleri():
            if self._beklemede(model):
                continue
            kalan = son_an - time.monotonic()
            if kalan < 2:
                break
            sonuc = self._gemini_dene(model, prompt, system_prompt, min(sure, kalan), json_schema)
            if sonuc is not None:
                return sonuc
        return None

    def _gemini_dene(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str],
        sure: float,
        json_schema: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Make one Gemini request; a rejected schema is retried once without it."""
        schema_kullan = bool(json_schema) and self._gemini_schema_destegi
        try:
            from google.genai import types

            response = self._gemini().models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt or None,
                    response_mime_type="application/json",
                    response_json_schema=json_schema if schema_kullan else None,
                    temperature=LLM_TEMPERATURE,
                    http_options=types.HttpOptions(timeout=int(sure * 1000)),
                ),
            )
            sonuc = self._extract_json(response.text or "")
            if sonuc is None:
                logger.warning("Gemini model %s returned a response that is not a JSON object", model)
            return sonuc
        except Exception as e:
            if schema_kullan and getattr(e, "code", None) == 400:
                logger.info("Gemini rejected the response schema; falling back to JSON mode")
                self._gemini_schema_destegi = False
                return self._gemini_dene(model, prompt, system_prompt, sure, None)
            self._beklemeye_al(model, e)
            return None

    def _watsonx(self):
        """Return the shared watsonx.ai model client, creating it on first use."""
        if self._watsonx_model is None:
            with self._lock:
                if self._watsonx_model is None:
                    from ibm_watsonx_ai import Credentials
                    from ibm_watsonx_ai.foundation_models import ModelInference

                    self._watsonx_model = ModelInference(
                        model_id=settings.WATSONX_MODEL_ID,
                        credentials=Credentials(url=settings.WATSONX_URL, api_key=settings.WATSONX_API_KEY),
                        project_id=settings.WATSONX_PROJECT_ID,
                    )
        return self._watsonx_model

    def _call_watsonx(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Call the IBM watsonx.ai API."""
        if not (settings.WATSONX_URL and settings.WATSONX_API_KEY and settings.WATSONX_PROJECT_ID):
            return None

        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            return self._extract_json(self._watsonx().generate_text(prompt=full_prompt))
        except Exception as e:
            logger.warning("watsonx request failed: %s", e)
            return None

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Safely parse a JSON object from an LLM response."""
        text = text.strip()
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                pass
        return None


llm_client = UniversalLLMClient()
