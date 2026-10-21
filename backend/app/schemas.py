import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import ProcessingStatus


class AuthorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    first_name: str | None
    last_name: str | None
    normalized_name: str


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size: int
    checksum: str
    processing_status: ProcessingStatus
    processing_error: str | None


class PaperRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    zotero_item_key: str | None
    title: str
    abstract: str | None
    doi: str | None
    journal: str | None
    publication_year: int | None
    url: str | None
    authors: list[AuthorRead] = []
    attachments: list[AttachmentRead] = []


class SectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    heading: str | None
    section_type: str | None
    section_order: int
    page_start: int | None
    page_end: int | None


class PaperDetail(PaperRead):
    sections: list[SectionRead] = []


class FacetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str


class LibraryFacets(BaseModel):
    collections: list[FacetRead]
    tags: list[FacetRead]


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=10_000)
    conversation_id: uuid.UUID | None = None
    top_k: int = Field(default=6, ge=1, le=20)


class CitationRead(BaseModel):
    chunk_id: uuid.UUID
    section: str | None
    page: int | None
    excerpt: str
    relevance_score: float


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    citations: list[CitationRead]


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role: str
    content: str
    model: str | None
    created_at: datetime


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    created_at: datetime
    messages: list[MessageRead]


class SyncResult(BaseModel):
    previous_version: int
    library_version: int
    papers_upserted: int
    collections_upserted: int
    deleted_items: int
