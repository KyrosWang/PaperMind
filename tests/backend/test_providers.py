import inspect
from collections.abc import AsyncIterator, Sequence

from app.services.providers import EmbeddingProvider, LLMProvider


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]


class FakeLLMProvider(LLMProvider):
    async def chat(self, messages: list[dict[str, str]]) -> str:
        return "grounded answer"

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        yield "grounded"
        yield " answer"


def test_provider_interfaces_are_replaceable() -> None:
    assert FakeEmbeddingProvider().embed(["abc"]) == [[3.0]]
    llm = FakeLLMProvider()
    assert isinstance(llm, LLMProvider)
    assert inspect.iscoroutinefunction(llm.chat)
    assert inspect.isasyncgenfunction(llm.stream_chat)
