import json
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

from openai import AsyncOpenAI, OpenAI

from app.config import Settings


class ProviderConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LLMResponse:
    answer: str
    citations: list[int]


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse: ...

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

    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        result = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            response_format={  # type: ignore[arg-type]
                "type": "json_schema",
                "json_schema": {
                    "name": "papermind_answer",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "answer": {"type": "string"},
                            "citations": {
                                "type": "array",
                                "items": {"type": "integer"},
                            },
                        },
                        "required": ["answer", "citations"],
                        "additionalProperties": False,
                    },
                },
            },
        )
        payload = json.loads(result.choices[0].message.content or "{}")
        answer = payload.get("answer")
        citations = payload.get("citations")
        if not isinstance(answer, str) or not isinstance(citations, list):
            raise ValueError("LLM returned an invalid structured answer")
        if any(not isinstance(index, int) or isinstance(index, bool) for index in citations):
            raise ValueError("LLM returned invalid citation indices")
        return LLMResponse(answer=answer, citations=citations)

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
