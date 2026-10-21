from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence

from openai import AsyncOpenAI, OpenAI

from app.config import Settings


class ProviderConfigurationError(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict[str, str]]) -> str: ...

    @abstractmethod
    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        yield ""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, dimensions: int) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        result = self.client.embeddings.create(
            model=self.model, input=list(texts), dimensions=self.dimensions
        )
        return [item.embedding for item in result.data]


class OpenAILLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def chat(self, messages: list[dict[str, str]]) -> str:
        result = await self.client.chat.completions.create(model=self.model, messages=messages)  # type: ignore[arg-type]
        return result.choices[0].message.content or ""

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,  # type: ignore[arg-type]
        )
        async for event in stream:
            if event.choices[0].delta.content:
                yield event.choices[0].delta.content


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider != "openai":
        raise ProviderConfigurationError(
            f"Unsupported embedding provider: {settings.embedding_provider}"
        )
    if not settings.openai_api_key:
        raise ProviderConfigurationError("OPENAI_API_KEY is required for embeddings")
    return OpenAIEmbeddingProvider(
        settings.openai_api_key,
        settings.openai_embedding_model,
        settings.embedding_dimension,
    )


def get_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider != "openai":
        raise ProviderConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")
    if not settings.openai_api_key:
        raise ProviderConfigurationError("OPENAI_API_KEY is required for chat")
    return OpenAILLMProvider(settings.openai_api_key, settings.openai_model)
