import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import DocumentChunk
from app.services.providers import EmbeddingProvider


@dataclass(slots=True)
class RetrievalResult:
    chunk: DocumentChunk
    score: float


def _rrf(ranks: dict[uuid.UUID, int], constant: int = 60) -> dict[uuid.UUID, float]:
    return {key: 1.0 / (constant + rank) for key, rank in ranks.items()}


def retrieve(
    db: Session,
    paper_id: uuid.UUID,
    query: str,
    top_k: int,
    embedding_provider: EmbeddingProvider | None,
) -> list[RetrievalResult]:
    """Combine PostgreSQL FTS and pgvector rankings with reciprocal-rank fusion."""
    base = (
        select(DocumentChunk)
        .options(joinedload(DocumentChunk.section))
        .where(DocumentChunk.paper_id == paper_id)
    )
    dialect = db.bind.dialect.name if db.bind else ""
    candidates: dict[uuid.UUID, DocumentChunk] = {}
    lexical_ids: list[uuid.UUID] = []
    semantic_ids: list[uuid.UUID] = []

    if dialect == "postgresql":
        vector = func.to_tsvector("english", DocumentChunk.text)
        tsquery = func.websearch_to_tsquery("english", query)
        lexical = db.scalars(
            base.where(vector.op("@@")(tsquery))
            .order_by(func.ts_rank_cd(vector, tsquery).desc())
            .limit(top_k * 3)
        ).all()
    else:
        terms = {term.casefold() for term in query.split() if len(term) > 2}
        all_chunks = db.scalars(base).all()
        lexical = sorted(
            all_chunks,
            key=lambda item: sum(item.text.casefold().count(term) for term in terms),
            reverse=True,
        )[: top_k * 3]

    for chunk in lexical:
        candidates[chunk.id] = chunk
        lexical_ids.append(chunk.id)

    if embedding_provider is not None and dialect == "postgresql":
        query_embedding = embedding_provider.embed([query])[0]
        semantic = db.scalars(
            base.where(DocumentChunk.embedding.is_not(None))
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k * 3)
        ).all()
        for chunk in semantic:
            candidates[chunk.id] = chunk
            semantic_ids.append(chunk.id)

    scores: dict[uuid.UUID, float] = {}
    for ranking in (
        _rrf({key: rank for rank, key in enumerate(lexical_ids, 1)}),
        _rrf({key: rank for rank, key in enumerate(semantic_ids, 1)}),
    ):
        for key, score in ranking.items():
            scores[key] = scores.get(key, 0.0) + score
    if not scores and candidates:
        scores = {key: 0.0 for key in candidates}
    ranked = sorted(scores, key=scores.get, reverse=True)[:top_k]  # type: ignore[arg-type]
    return [RetrievalResult(candidates[key], scores[key]) for key in ranked]
