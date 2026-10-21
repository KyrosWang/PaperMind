"""Initial PaperMind schema.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    processing_status = postgresql.ENUM(
        "pending",
        "parsing",
        "embedding",
        "ready",
        "failed",
        name="processingstatus",
        create_type=False,
    )
    processing_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "papers",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("zotero_item_key", sa.String(32), unique=True),
        sa.Column("zotero_version", sa.Integer),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("abstract", sa.Text),
        sa.Column("doi", sa.String(255)),
        sa.Column("pmid", sa.String(64)),
        sa.Column("arxiv_id", sa.String(64)),
        sa.Column("journal", sa.Text),
        sa.Column("publication_year", sa.Integer),
        sa.Column("url", sa.Text),
        sa.Column("date_added", sa.DateTime(timezone=True)),
        sa.Column("date_modified", sa.DateTime(timezone=True)),
        sa.Column("zotero_deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_papers_zotero_item_key", "papers", ["zotero_item_key"])
    op.create_index("ix_papers_doi", "papers", ["doi"])
    op.create_index("ix_papers_publication_year", "papers", ["publication_year"])
    op.create_table(
        "authors",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("first_name", sa.String(255)),
        sa.Column("last_name", sa.String(255)),
        sa.Column("normalized_name", sa.String(511), nullable=False, unique=True),
    )
    op.create_table(
        "collections",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("zotero_collection_key", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("parent_collection_id", UUID, sa.ForeignKey("collections.id")),
    )
    op.create_table(
        "tags",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
    )
    op.create_table(
        "paper_authors",
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("author_id", UUID, sa.ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("author_order", sa.Integer, nullable=False),
    )
    op.create_table(
        "paper_collections",
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("collection_id", UUID, sa.ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "paper_tags",
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", UUID, sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "attachments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.Text, nullable=False, unique=True),
        sa.Column("mime_type", sa.String(127), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processing_status", processing_status, nullable=False),
        sa.Column("processing_error", sa.Text),
        sa.UniqueConstraint("paper_id", "checksum"),
    )
    op.create_index("ix_attachments_paper_id", "attachments", ["paper_id"])
    op.create_index("ix_attachments_checksum", "attachments", ["checksum"])
    op.create_index("ix_attachments_processing_status", "attachments", ["processing_status"])
    op.create_table(
        "document_sections",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_type", sa.String(64)),
        sa.Column("heading", sa.Text),
        sa.Column("section_order", sa.Integer, nullable=False),
        sa.Column("page_start", sa.Integer),
        sa.Column("page_end", sa.Integer),
    )
    op.create_index("ix_document_sections_paper_id", "document_sections", ["paper_id"])
    op.create_table(
        "document_chunks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", UUID, sa.ForeignKey("document_sections.id", ondelete="SET NULL")),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("page_start", sa.Integer),
        sa.Column("page_end", sa.Integer),
        sa.Column("token_count", sa.Integer, nullable=False),
        sa.Column("embedding", Vector()),
        sa.UniqueConstraint("paper_id", "chunk_index"),
    )
    op.create_index("ix_document_chunks_paper_id", "document_chunks", ["paper_id"])
    op.create_index("ix_document_chunks_paper_section", "document_chunks", ["paper_id", "section_id"])
    op.create_index(
        "ix_document_chunks_fts",
        "document_chunks",
        [sa.text("to_tsvector('english', text)")],
        postgresql_using="gin",
    )
    op.create_table(
        "conversations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("paper_id", UUID, sa.ForeignKey("papers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_conversations_paper_id", "conversations", ["paper_id"])
    op.create_table(
        "messages",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("conversation_id", UUID, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("model", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table(
        "citation_evidence",
        sa.Column("message_id", UUID, sa.ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("chunk_id", UUID, sa.ForeignKey("document_chunks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("relevance_score", sa.Float, nullable=False),
    )
    op.create_table(
        "zotero_sync_state",
        sa.Column("library_type", sa.String(16), primary_key=True),
        sa.Column("library_id", sa.String(64), primary_key=True),
        sa.Column("library_version", sa.Integer, nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    for table in [
        "citation_evidence",
        "messages",
        "conversations",
        "document_chunks",
        "document_sections",
        "attachments",
        "paper_tags",
        "paper_collections",
        "paper_authors",
        "tags",
        "collections",
        "authors",
        "zotero_sync_state",
        "papers",
    ]:
        op.drop_table(table)
    postgresql.ENUM(name="processingstatus").drop(op.get_bind(), checkfirst=True)

