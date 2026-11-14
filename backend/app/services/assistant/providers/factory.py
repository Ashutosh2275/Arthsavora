"""
Arthsavora LLM Provider Factory
Resolves the active LLM provider based on application configuration and environment variables.
Defaults to MockDeterministicProvider when external credentials are unconfigured.
"""

from typing import Optional
from app.core.config import settings
from app.services.assistant.providers.base_provider import BaseLLMProvider
from app.services.assistant.providers.gemini_provider import GeminiProvider
from app.services.assistant.providers.mock_provider import MockDeterministicProvider
from app.services.assistant.providers.openai_provider import OpenAICompatibleProvider


def get_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseLLMProvider:
    """
    Factory resolving configured LLM adapter with safe deterministic fallback.
    """
    p_name = (provider_name or getattr(settings, "AI_ASSISTANT_PROVIDER", "mock")).lower().strip()
    m_name = model_name or getattr(settings, "AI_ASSISTANT_MODEL", "mock-fin-v1")

    if p_name == "gemini":
        api_key = getattr(settings, "GEMINI_API_KEY", "")
        if api_key and "placeholder" not in api_key:
            return GeminiProvider(api_key=api_key, model_name=m_name)
        # Fallback to mock provider if key is missing
        return MockDeterministicProvider(model_name=m_name)

    elif p_name in ("openai", "ollama", "local"):
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        base_url = getattr(settings, "OPENAI_BASE_URL", "https://api.openai.com/v1")
        return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model_name=m_name)

    # Default: Deterministic mock provider
    return MockDeterministicProvider(model_name=m_name)
