from collections.abc import AsyncGenerator, Sequence
from typing import Any, Protocol, runtime_checkable

from openai import AsyncOpenAI, OpenAI
from groq import AsyncGroq, Groq

from app.core.config import settings

@runtime_checkable
class LLMClient(Protocol):
    def chat_completion(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Any:
        ...

    def stream_chat(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Any:
        ...

    async def async_stream_chat(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        ...
        yield ""  # make type checker happy

class DeepSeekClient:
    """Thin wrapper around the DeepSeek OpenAI-compatible chat API."""

    def __init__(self) -> None:
        self._client: OpenAI | None = None
        self._async_client: AsyncOpenAI | None = None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            if not settings.deepseek_api_key:
                raise ValueError("DEEPSEEK_API_KEY is not configured.")
            self._client = OpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                timeout=settings.deepseek_timeout,
            )
        return self._client

    def _get_async_client(self) -> AsyncOpenAI:
        if self._async_client is None:
            if not settings.deepseek_api_key:
                raise ValueError("DEEPSEEK_API_KEY is not configured.")
            self._async_client = AsyncOpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                timeout=settings.deepseek_timeout,
            )
        return self._async_client

    def chat_completion(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Any:
        client = self._get_client()
        return client.chat.completions.create(
            model=model or settings.deepseek_model,
            messages=list(messages),
            temperature=temperature,
            **kwargs,
        )

    def stream_chat(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Any:
        client = self._get_client()
        return client.chat.completions.create(
            model=model or settings.deepseek_model,
            messages=list(messages),
            temperature=temperature,
            stream=True,
            **kwargs,
        )

    async def async_stream_chat(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        client = self._get_async_client()
        stream = await client.chat.completions.create(
            model=model or settings.deepseek_model,
            messages=list(messages),
            temperature=temperature,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

class GroqClient:
    """Client for Groq Cloud API."""

    def __init__(self) -> None:
        self._client: Groq | None = None
        self._async_client: AsyncGroq | None = None

    def _get_client(self) -> Groq:
        if self._client is None:
            if not settings.groq_api_key:
                raise ValueError("GROQ_API_KEY is not configured.")
            self._client = Groq(
                api_key=settings.groq_api_key,
                timeout=settings.deepseek_timeout or 30,
            )
        return self._client

    def _get_async_client(self) -> AsyncGroq:
        if self._async_client is None:
            if not settings.groq_api_key:
                raise ValueError("GROQ_API_KEY is not configured.")
            self._async_client = AsyncGroq(
                api_key=settings.groq_api_key,
                timeout=settings.deepseek_timeout or 30,
            )
        return self._async_client

    def chat_completion(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Any:
        client = self._get_client()
        return client.chat.completions.create(
            model=model or settings.groq_model,
            messages=list(messages),
            temperature=temperature,
            **kwargs,
        )

    def stream_chat(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Any:
        client = self._get_client()
        return client.chat.completions.create(
            model=model or settings.groq_model,
            messages=list(messages),
            temperature=temperature,
            stream=True,
            **kwargs,
        )

    async def async_stream_chat(
        self,
        messages: Sequence[dict[str, Any]],
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        client = self._get_async_client()
        stream = await client.chat.completions.create(
            model=model or settings.groq_model,
            messages=list(messages),
            temperature=temperature,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content

def get_llm_client() -> LLMClient:
    """Factory to get the preferred LLM client based on settings."""
    if settings.llm_provider.lower() == "groq":
        return GroqClient()
    return DeepSeekClient()

# Default shared client
llm_client = get_llm_client()
