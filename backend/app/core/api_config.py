"""LLM API configuration and key settings.

Configure Google Gemini, IBM watsonx, OpenAI, DeepSeek, Groq, OpenRouter,
or a local Ollama/vLLM model here.

SECURITY NOTE:
Set API keys in the backend/.env file using the appropriate environment variable.
"""


CUSTOM_LLM_API_KEY = ""

CUSTOM_LLM_BASE_URL = "https://api.openai.com/v1"

CUSTOM_LLM_MODEL = "gpt-4o-mini"



GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-3.8-flash"

WATSONX_API_KEY = ""
WATSONX_PROJECT_ID = ""
WATSONX_URL = "https://us-south.ml.cloud.ibm.com"
WATSONX_MODEL_ID = "ibm/granite-13b-chat-v2"
