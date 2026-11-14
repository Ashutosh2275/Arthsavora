"""
Arthsavora OpenAI-Compatible LLM Provider Adapter
Supports OpenAI, Ollama, vLLM, and LocalAI endpoints using standard Chat Completions JSON.
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


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI / Ollama / LocalAI compatible provider adapter."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model_name: str = "gpt-4o-mini",
    ):
        self.api_key = api_key or "local"
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_tools=True,
            supports_streaming=True,
            supports_structured_output=True,
            max_context_tokens=16384,
        )

    async def generate_completion(
        self,
        messages: List[LLMMessage],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        api_messages = [{"role": "system", "content": system_prompt}]
        for m in messages:
            api_messages.append({"role": m.role, "content": m.content})

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": api_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"OpenAI endpoint returned {res.status_code}: {res.text}")
            data = res.json()
            choice = data["choices"][0]
            content = choice["message"].get("content") or ""
            return LLMResponse(content=content, model_name=self.model_name)

    async def generate_stream(
        self,
        messages: List[LLMMessage],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[LLMStreamChunk]:
        comp = await self.generate_completion(messages, system_prompt, tools, temperature, max_tokens)
        words = comp.content.split(" ")
        for i, w in enumerate(words):
            yield LLMStreamChunk(delta_text=(" " if i > 0 else "") + w)
        yield LLMStreamChunk(is_finish=True)
