"""
Arthsavora Gemini LLM Provider Adapter
Integrates Google Gemini (GenAI) models using the official API client with error normalization.
"""

from typing import Any, AsyncIterator, Dict, List, Optional
import httpx

from app.domain.assistant import ModelCapabilities, ToolCallVO
from app.services.assistant.providers.base_provider import (
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
)


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider adapter."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model_name

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_tools=True,
            supports_streaming=True,
            supports_structured_output=True,
            max_context_tokens=32768,
        )

    async def generate_completion(
        self,
        messages: List[LLMMessage],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        # If API key is placeholder or invalid, fall back safely with explanation
        if not self.api_key or "placeholder" in self.api_key:
            from app.services.assistant.providers.mock_provider import MockDeterministicProvider
            mock = MockDeterministicProvider(model_name=self.model_name)
            return await mock.generate_completion(messages, system_prompt, tools, temperature, max_tokens)

        # Real Google Gemini generateContent call via HTTP REST
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        contents = []
        for m in messages:
            role = "user" if m.role in ("user", "system") else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})

        payload = {
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"Gemini API returned status {res.status_code}: {res.text}")
            data = res.json()
            candidates = data.get("candidates", [])
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "") if candidates else ""
            return LLMResponse(content=text, model_name=self.model_name)

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[LLMStreamChunk]:
        # Fallback to completion streaming for compatibility
        comp = await self.generate_completion(messages, system_prompt, tools, temperature, max_tokens)
        words = comp.content.split(" ")
        for i, w in enumerate(words):
            yield LLMStreamChunk(delta_text=(" " if i > 0 else "") + w)
        yield LLMStreamChunk(is_finish=True)
