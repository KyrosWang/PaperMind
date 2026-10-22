import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import Settings, get_settings
from app.database import get_db
from app.models import (
    CitationEvidence,
    Conversation,
    Message,
    Paper,
    RetrievedEvidence,
)
from app.schemas import ChatRequest, ChatResponse, CitationRead, ConversationRead
from app.services.providers import (
    ProviderConfigurationError,
    get_embedding_provider,
    get_llm_provider,
)
from app.services.retrieval import retrieve

router = APIRouter()

SYSTEM_PROMPT = """You are PaperMind, a scientific reading assistant. Answer the user's
question primarily from the numbered excerpts supplied from the current paper. Cite supporting
excerpts inline as [1], [2], etc. Clearly label any general background knowledge that is not in
the excerpts. Never invent evidence, section names, or page numbers. If the excerpts are
insufficient, say so plainly and explain what is missing. Return a structured answer containing
the answer text and a list of the numeric excerpt indices you actually cited. Only cite indices
from the supplied excerpts."""


@router.post("/{paper_id}/chat", response_model=ChatResponse)
async def chat_with_paper(
    paper_id: uuid.UUID,
    payload: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    paper = db.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    if payload.conversation_id:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.id == payload.conversation_id,
                Conversation.paper_id == paper_id,
            )
        )
        if conversation is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(paper_id=paper_id, title=payload.question[:100])
        db.add(conversation)
        db.flush()
    last_message_order = db.scalar(
        select(func.max(Message.message_order)).where(Message.conversation_id == conversation.id)
    )
    current_message_order = (last_message_order if last_message_order is not None else -1) + 1
    history = list(
        reversed(
            db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.message_order.desc())
                .limit(settings.chat_history_messages)
            ).all()
        )
    )
    db.add(
        Message(
            conversation_id=conversation.id,
            role="user",
            content=payload.question,
            message_order=current_message_order,
        )
    )
    db.commit()

    try:
        embedding_provider = get_embedding_provider(settings)
    except ProviderConfigurationError:
        embedding_provider = None
    results = retrieve(db, paper_id, payload.question, payload.top_k, embedding_provider)
    if not results:
        raise HTTPException(
            status_code=409,
            detail="No processed text is available for this paper. Upload and process a PDF first.",
        )
    evidence_text = []
    for index, result in enumerate(results, 1):
        section = result.chunk.section.heading if result.chunk.section else "Unknown section"
        page = result.chunk.page_start or "unknown"
        evidence_text.append(f"[{index}] Section: {section}; Page: {page}\n{result.chunk.text}")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend({"role": item.role, "content": item.content} for item in history)
    messages.append(
        {
            "role": "user",
            "content": (
                f"Paper: {paper.title}\n\nEvidence excerpts:\n\n"
                + "\n\n".join(evidence_text)
                + f"\n\nQuestion: {payload.question}"
            ),
        }
    )
    try:
        provider = get_llm_provider(settings)
        response = await provider.chat(messages)
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="LLM provider request failed") from exc

    assistant = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response.answer,
        model=settings.openai_model,
        message_order=current_message_order + 1,
    )
    db.add(assistant)
    db.flush()
    citations: list[CitationRead] = []
    for index, result in enumerate(results, 1):
        db.add(
            RetrievedEvidence(
                message_id=assistant.id,
                chunk_id=result.chunk.id,
                evidence_index=index,
                relevance_score=result.score,
            )
        )
    valid_indices: list[int] = []
    for index in response.citations:
        if (
            isinstance(index, int)
            and not isinstance(index, bool)
            and 1 <= index <= len(results)
            and index not in valid_indices
        ):
            valid_indices.append(index)
    for index in valid_indices:
        result = results[index - 1]
        db.add(
            CitationEvidence(
                message_id=assistant.id,
                chunk_id=result.chunk.id,
                evidence_index=index,
                relevance_score=result.score,
            )
        )
        citations.append(
            CitationRead(
                evidence_index=index,
                chunk_id=result.chunk.id,
                section=result.chunk.section.heading if result.chunk.section else None,
                page=result.chunk.page_start,
                excerpt=result.chunk.text[:400],
                relevance_score=result.score,
            )
        )
    db.commit()
    return ChatResponse(
        conversation_id=conversation.id,
        message_id=assistant.id,
        answer=response.answer,
        citations=citations,
    )


@router.get("/{paper_id}/conversations", response_model=list[ConversationRead])
def conversation_history(
    paper_id: uuid.UUID, db: Annotated[Session, Depends(get_db)]
) -> list[Conversation]:
    return list(
        db.scalars(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.paper_id == paper_id)
            .order_by(Conversation.created_at.desc())
        ).all()
    )
