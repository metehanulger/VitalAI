"""Universal LLM client.

Supports OpenAI-compatible providers, local models, Google Gemini, and IBM watsonx.ai.
API keys and model information are read from environment variables or constructor parameters.
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
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


class UniversalLLMClient:
    """Flexible adapter for connecting to LLM APIs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ):
        self.api_key = (
            api_key
            or getattr(settings, "LLM_API_KEY", "")
            or (getattr(api_config, "CUSTOM_LLM_API_KEY", "") if api_config else "")
            or os.getenv("LLM_API_KEY", "")
        )

        self.base_url = (
            base_url
            or getattr(settings, "LLM_BASE_URL", "")
            or (getattr(api_config, "CUSTOM_LLM_BASE_URL", "") if api_config else "")
            or os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        ).rstrip("/")

        self.model = (
            model
            or getattr(settings, "LLM_MODEL", "")
            or (getattr(api_config, "CUSTOM_LLM_MODEL", "") if api_config else "")
            or os.getenv("LLM_MODEL", "gpt-4o-mini")
        )

        configured_provider = (
            provider
            or getattr(settings, "LLM_PROVIDER", "")
            or os.getenv("LLM_PROVIDER", "openai_compatible")
        ).lower()
        gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        self.provider = (
            "gemini"
            if configured_provider == "openai_compatible" and not self.api_key and gemini_key
            else configured_provider
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Send a prompt to the configured LLM and return its JSON response."""
        gemini_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if self.provider == "gemini" or (not self.api_key and gemini_key):
            res = self._call_gemini(prompt, system_prompt)
            if res:
                return res

        watsonx_key = getattr(settings, "WATSONX_API_KEY", "") or os.getenv("WATSONX_API_KEY", "")
        if self.provider == "watsonx" or (not self.api_key and watsonx_key):
            res = self._call_watsonx(prompt, system_prompt)
            if res:
                return res

        if not self.api_key and self.base_url.rstrip("/").lower() == DEFAULT_OPENAI_BASE_URL:
            logger.debug("LLM request skipped: no API key is configured for the default OpenAI endpoint")
            return None

        return self._call_openai_compatible(prompt, system_prompt)

    def _call_openai_compatible(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Call a standard OpenAI-compatible REST API using urllib."""
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
            logger.warning(f"LLM API error ({e.code}): {error_body}")
        except Exception as e:
            logger.warning(f"LLM API connection error: {e}")

        return None

    def _call_gemini(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Call the Google Gemini API."""
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
            model_name = getattr(settings, "GEMINI_MODEL", "gemini-3.8-flash")
            model = genai.GenerativeModel(model_name)

            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = model.generate_content(full_prompt)
            return self._extract_json(response.text)
        except Exception as e:
            logger.warning(f"Gemini request failed: {e}")
            return None

    def _call_watsonx(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Call the IBM watsonx.ai API."""
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
            logger.warning(f"watsonx request failed: {e}")
            return None

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """Safely parse a JSON object from an LLM response."""
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
        return None


llm_client = UniversalLLMClient()
