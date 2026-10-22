import inspect
from collections.abc import AsyncIterator, Sequence

from app.services.providers import EmbeddingProvider, LLMProvider, LLMResponse


class FakeEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]


class FakeLLMProvider(LLMProvider):
    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        return LLMResponse("grounded answer [1]", [1])

    async def stream_chat(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        yield "grounded"
        yield " answer"


def test_provider_interfaces_are_replaceable() -> None:
    assert FakeEmbeddingProvider().embed(["abc"]) == [[3.0]]
    llm = FakeLLMProvider()
    assert isinstance(llm, LLMProvider)
    assert inspect.iscoroutinefunction(llm.chat)
    assert inspect.isasyncgenfunction(llm.stream_chat)
    coroutine = llm.chat([])
    try:
        coroutine.send(None)
    except StopIteration as completed:
        assert completed.value.citations == [1]
    else:
        raise AssertionError("Fake provider unexpectedly suspended")
