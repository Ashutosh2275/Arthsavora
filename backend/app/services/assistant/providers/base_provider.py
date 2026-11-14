"""
Arthsavora LLM Provider Abstraction Layer
Base interface for model-agnostic chat completions, tool execution orchestration,
and streaming responses across commercial and self-hosted runtimes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional
from app.domain.assistant import ModelCapabilities, ToolCallVO


@dataclass
class LLMMessage:
    """Standardized chat message payload across providers."""
    role: str  # user, assistant, system, tool
    content: str
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class LLMResponse:
    """Standardized completion response from an LLM provider."""
    content: str
    tool_calls: List[ToolCallVO] = field(default_factory=list)
    tokens_prompt: int = 0
    tokens_completion: int = 0
    finish_reason: str = "stop"  # stop, tool_calls, length, content_filter
    model_name: str = "mock-fin-v1"


@dataclass
class LLMStreamChunk:
    """Single incremental chunk delivered during server-sent response streaming."""
    delta_text: str = ""
    tool_call_delta: Optional[ToolCallVO] = None
    is_finish: bool = False
    tokens_prompt: int = 0
    tokens_completion: int = 0


class BaseLLMProvider(ABC):
    """Abstract base contract for AI model integration adapters."""

    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities:
        """Returns verified capabilities for the active model."""
        pass

    @abstractmethod
    async def generate_completion(
        self,
        messages: List[LLMMessage],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        """Generates a complete non-streaming response turn."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> AsyncIterator[LLMStreamChunk]:
        """Streams response tokens incrementally."""
        pass
