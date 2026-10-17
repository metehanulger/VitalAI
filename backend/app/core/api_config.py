"""LLM API Yapılandırma ve Anahtar Dosyası.

Bu dosya, projede kullanılacak Büyük Dil Modeli (LLM) API bilgilerini tanımlar.
Sadece Google Gemini veya IBM watsonx ile sınırlı kalmadan; OpenAI, DeepSeek, Groq,
Anthropic (OpenRouter) veya yerel Ollama/vLLM gibi dilediğiniz herhangi bir LLM'i
buradaki alanları doldurarak kullanabilirsiniz.

GÜVENLİK NOTU:
Gerçek API anahtarınızı buraya yazabilir veya doğrudan backend/.env dosyasında
LLM_API_KEY değişkenine tanımlayabilirsiniz.
"""

# =====================================================================
# 1. EVRENSEL LLM API AYARLARI (İSTEDİĞİNİZ HERHANGİ BİR MODEL)
# =====================================================================

# API Anahtarınızı tırnak içine yazınız (Varsayılan olarak boş bırakılmıştır):
CUSTOM_LLM_API_KEY = ""

# Kullanmak istediğiniz sağlayıcının Base URL adresi:
# - OpenAI için:     "https://api.openai.com/v1"
# - DeepSeek için:   "https://api.deepseek.com"
# - Groq için:       "https://api.groq.com/openai/v1"
# - OpenRouter için: "https://openrouter.ai/api/v1"
# - Yerel Ollama:    "http://localhost:11434/v1"
CUSTOM_LLM_BASE_URL = "https://api.openai.com/v1"

# Model Adı:
# - OpenAI:     "gpt-4o-mini" veya "gpt-4o"
# - DeepSeek:   "deepseek-chat" veya "deepseek-reasoner"
# - Groq:       "llama-3.3-70b-versatile"
# - Ollama:     "llama3" veya "qwen2.5"
CUSTOM_LLM_MODEL = "gpt-4o-mini"


# =====================================================================
# 2. ALTERNATİF SAĞLAYICILAR (GEMINI VEYA WATSONX KULLANMAK İSTERSENİZ)
# =====================================================================

# Google Gemini API Anahtarı (Boş bırakılmıştır):
GEMINI_API_KEY = ""
GEMINI_MODEL = "gemini-1.5-flash"

# IBM watsonx.ai Anahtarları (Boş bırakılmıştır):
WATSONX_API_KEY = ""
WATSONX_PROJECT_ID = ""
WATSONX_URL = "https://us-south.ml.cloud.ibm.com"
WATSONX_MODEL_ID = "ibm/granite-13b-chat-v2"
