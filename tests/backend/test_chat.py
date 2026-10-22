from pathlib import Path

from app.api.routes import chat as chat_routes
from app.config import Settings
from app.models import (
    Attachment,
    CitationEvidence,
    DocumentChunk,
    DocumentSection,
    Message,
    Paper,
    RetrievedEvidence,
)
from app.schemas import ChatRequest
from app.services.providers import LLMResponse
from app.services.retrieval import RetrievalResult
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, str]]] = []
        self.responses = [
            LLMResponse("The first answer [1].", [1]),
            LLMResponse("They chose it for the second reason [2].", [2, 99, 2, "bad"]),  # type: ignore[list-item]
        ]

    async def chat(self, messages: list[dict[str, str]]) -> LLMResponse:
        self.calls.append(messages)
        return self.responses.pop(0)


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite+pysqlite:///:memory:",
        data_root=tmp_path,
        chat_history_messages=8,
    )


def _run_immediate(coroutine):
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    raise AssertionError("Test coroutine unexpectedly suspended")


def test_follow_up_uses_history_and_persists_only_actual_citations(
    db: Session, tmp_path: Path, monkeypatch
) -> None:
    paper = Paper(title="Conversational paper")
    db.add(paper)
    db.flush()
    attachment = Attachment(
        paper_id=paper.id,
        filename="original.pdf",
        original_filename="paper.pdf",
        storage_path="paper.pdf",
        checksum="paper",
        file_size=10,
    )
    db.add(attachment)
    db.flush()
    paper.active_attachment_id = attachment.id
    section = DocumentSection(
        paper_id=paper.id,
        attachment_id=attachment.id,
        heading="Methods",
        section_order=0,
    )
    db.add(section)
    db.flush()
    chunks = [
        DocumentChunk(
            paper_id=paper.id,
            attachment_id=attachment.id,
            section_id=section.id,
            text="First retrieved excerpt",
            chunk_index=0,
            token_count=3,
        ),
        DocumentChunk(
            paper_id=paper.id,
            attachment_id=attachment.id,
            section_id=section.id,
            text="Second retrieved excerpt",
            chunk_index=1,
            token_count=3,
        ),
    ]
    db.add_all(chunks)
    db.commit()

    fake = FakeLLM()
    monkeypatch.setattr(chat_routes, "get_llm_provider", lambda _settings: fake)
    monkeypatch.setattr(chat_routes, "get_embedding_provider", lambda _settings: None)
    monkeypatch.setattr(
        chat_routes,
        "retrieve",
        lambda *_args: [RetrievalResult(chunks[0], 0.9), RetrievalResult(chunks[1], 0.8)],
    )

    first = _run_immediate(
        chat_routes.chat_with_paper(
            paper.id,
            ChatRequest(question="What method did they use?"),
            db,
            _settings(tmp_path),
        )
    )
    second = _run_immediate(
        chat_routes.chat_with_paper(
            paper.id,
            ChatRequest(
                question="Why did they choose that method?",
                conversation_id=first.conversation_id,
            ),
            db,
            _settings(tmp_path),
        )
    )

    assert [message["role"] for message in fake.calls[1]] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert fake.calls[1][1]["content"] == "What method did they use?"
    assert fake.calls[1][2]["content"] == "The first answer [1]."
    assert "Why did they choose that method?" in fake.calls[1][3]["content"]
    assert db.scalar(select(func.count()).select_from(Message)) == 4
    assert db.scalar(select(func.count()).select_from(RetrievedEvidence)) == 4

    second_citations = db.scalars(
        select(CitationEvidence).where(CitationEvidence.message_id == second.message_id)
    ).all()
    assert [(item.evidence_index, item.chunk_id) for item in second_citations] == [
        (2, chunks[1].id)
    ]
    assert [citation.evidence_index for citation in second.citations] == [2]
