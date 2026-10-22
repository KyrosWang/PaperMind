"""Stabilize active PDFs, evidence semantics, and author ordering.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("attachments", sa.Column("processing_token", UUID, nullable=True))
    op.add_column("papers", sa.Column("active_attachment_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_papers_active_attachment_id",
        "papers",
        "attachments",
        ["active_attachment_id"],
        ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )
    op.create_index("ix_papers_active_attachment_id", "papers", ["active_attachment_id"])
    op.execute(
        """
        UPDATE papers AS paper
        SET active_attachment_id = (
            SELECT attachment.id
            FROM attachments AS attachment
            WHERE attachment.paper_id = paper.id
            ORDER BY attachment.uploaded_at, attachment.id
            LIMIT 1
        )
        WHERE paper.active_attachment_id IS NULL
        """
    )

    op.add_column("document_sections", sa.Column("attachment_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_document_sections_attachment_id",
        "document_sections",
        "attachments",
        ["attachment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_document_sections_attachment_id", "document_sections", ["attachment_id"]
    )
    op.execute(
        """
        UPDATE document_sections AS section
        SET attachment_id = paper.active_attachment_id
        FROM papers AS paper
        WHERE section.paper_id = paper.id
        """
    )

    op.add_column("document_chunks", sa.Column("attachment_id", UUID, nullable=True))
    op.create_foreign_key(
        "fk_document_chunks_attachment_id",
        "document_chunks",
        "attachments",
        ["attachment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_document_chunks_attachment_id", "document_chunks", ["attachment_id"])
    op.execute(
        """
        UPDATE document_chunks AS chunk
        SET attachment_id = paper.active_attachment_id
        FROM papers AS paper
        WHERE chunk.paper_id = paper.id
        """
    )
    op.execute("DELETE FROM document_chunks WHERE attachment_id IS NULL")
    op.execute("DELETE FROM document_sections WHERE attachment_id IS NULL")
    op.alter_column("document_sections", "attachment_id", nullable=False)
    op.alter_column("document_chunks", "attachment_id", nullable=False)
    op.drop_constraint(
        "document_chunks_paper_id_chunk_index_key", "document_chunks", type_="unique"
    )
    op.create_unique_constraint(
        "uq_document_chunks_attachment_index",
        "document_chunks",
        ["attachment_id", "chunk_index"],
    )
    op.drop_index("ix_document_chunks_paper_section", table_name="document_chunks")
    op.create_index(
        "ix_document_chunks_attachment_section",
        "document_chunks",
        ["attachment_id", "section_id"],
    )

    op.create_table(
        "retrieved_evidence",
        sa.Column(
            "message_id",
            UUID,
            sa.ForeignKey("messages.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "chunk_id",
            UUID,
            sa.ForeignKey("document_chunks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("evidence_index", sa.Integer, nullable=False),
        sa.Column("relevance_score", sa.Float, nullable=False),
    )
    op.add_column("citation_evidence", sa.Column("evidence_index", sa.Integer, nullable=True))
    op.execute(
        """
        WITH numbered AS (
            SELECT message_id, chunk_id,
                   row_number() OVER (PARTITION BY message_id ORDER BY chunk_id) AS position
            FROM citation_evidence
        )
        UPDATE citation_evidence AS citation
        SET evidence_index = numbered.position
        FROM numbered
        WHERE citation.message_id = numbered.message_id
          AND citation.chunk_id = numbered.chunk_id
        """
    )
    op.alter_column("citation_evidence", "evidence_index", nullable=False)

    op.add_column("messages", sa.Column("message_order", sa.Integer, nullable=True))
    op.execute(
        """
        WITH ordered AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY conversation_id ORDER BY created_at, id
                   ) - 1 AS position
            FROM messages
        )
        UPDATE messages AS message
        SET message_order = ordered.position
        FROM ordered
        WHERE message.id = ordered.id
        """
    )
    op.alter_column("messages", "message_order", nullable=False)
    op.create_unique_constraint(
        "uq_messages_conversation_order",
        "messages",
        ["conversation_id", "message_order"],
    )

    op.drop_constraint("authors_normalized_name_key", "authors", type_="unique")
    op.execute(
        """
        CREATE TEMP TABLE papermind_author_replacements ON COMMIT DROP AS
        SELECT link.paper_id, link.author_id AS old_author_id, gen_random_uuid() AS new_author_id
        FROM paper_authors AS link
        """
    )
    op.execute(
        """
        INSERT INTO authors (id, first_name, last_name, normalized_name)
        SELECT replacement.new_author_id, author.first_name, author.last_name,
               author.normalized_name
        FROM papermind_author_replacements AS replacement
        JOIN authors AS author ON author.id = replacement.old_author_id
        """
    )
    op.execute(
        """
        UPDATE paper_authors AS link
        SET author_id = replacement.new_author_id
        FROM papermind_author_replacements AS replacement
        WHERE link.paper_id = replacement.paper_id
          AND link.author_id = replacement.old_author_id
        """
    )
    op.execute(
        """
        DELETE FROM authors AS author
        WHERE NOT EXISTS (
            SELECT 1 FROM paper_authors AS link WHERE link.author_id = author.id
        )
        """
    )
    op.add_column(
        "paper_authors",
        sa.Column("creator_type", sa.String(32), nullable=False, server_default="author"),
    )
    op.execute(
        """
        WITH ordered AS (
            SELECT paper_id, author_id,
                   row_number() OVER (
                       PARTITION BY paper_id ORDER BY author_order, author_id
                   ) - 1 AS position
            FROM paper_authors
        )
        UPDATE paper_authors AS link
        SET author_order = ordered.position
        FROM ordered
        WHERE link.paper_id = ordered.paper_id AND link.author_id = ordered.author_id
        """
    )
    op.create_unique_constraint(
        "uq_paper_authors_paper_order", "paper_authors", ["paper_id", "author_order"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_paper_authors_paper_order", "paper_authors", type_="unique")
    op.drop_column("paper_authors", "creator_type")
    op.execute(
        """
        CREATE TEMP TABLE papermind_author_canonical ON COMMIT DROP AS
        SELECT normalized_name, min(id::text)::uuid AS canonical_id
        FROM authors
        GROUP BY normalized_name
        """
    )
    op.execute(
        """
        DELETE FROM paper_authors AS link
        USING authors AS author, papermind_author_canonical AS canonical
        WHERE link.author_id = author.id
          AND author.normalized_name = canonical.normalized_name
          AND author.id <> canonical.canonical_id
          AND EXISTS (
              SELECT 1 FROM paper_authors AS existing
              WHERE existing.paper_id = link.paper_id
                AND existing.author_id = canonical.canonical_id
          )
        """
    )
    op.execute(
        """
        UPDATE paper_authors AS link
        SET author_id = canonical.canonical_id
        FROM authors AS author, papermind_author_canonical AS canonical
        WHERE link.author_id = author.id
          AND author.normalized_name = canonical.normalized_name
          AND author.id <> canonical.canonical_id
        """
    )
    op.execute(
        """
        DELETE FROM authors AS author
        USING papermind_author_canonical AS canonical
        WHERE author.normalized_name = canonical.normalized_name
          AND author.id <> canonical.canonical_id
        """
    )
    op.create_unique_constraint(
        "authors_normalized_name_key", "authors", ["normalized_name"]
    )

    op.drop_constraint("uq_messages_conversation_order", "messages", type_="unique")
    op.drop_column("messages", "message_order")

    op.drop_column("citation_evidence", "evidence_index")
    op.drop_table("retrieved_evidence")

    op.drop_index("ix_document_chunks_attachment_section", table_name="document_chunks")
    op.create_index(
        "ix_document_chunks_paper_section", "document_chunks", ["paper_id", "section_id"]
    )
    op.drop_constraint(
        "uq_document_chunks_attachment_index", "document_chunks", type_="unique"
    )
    op.execute(
        """
        DELETE FROM document_chunks AS chunk
        USING papers AS paper
        WHERE chunk.paper_id = paper.id
          AND chunk.attachment_id <> paper.active_attachment_id
        """
    )
    op.execute(
        """
        DELETE FROM document_sections AS section
        USING papers AS paper
        WHERE section.paper_id = paper.id
          AND section.attachment_id <> paper.active_attachment_id
        """
    )
    op.create_unique_constraint(
        "document_chunks_paper_id_chunk_index_key",
        "document_chunks",
        ["paper_id", "chunk_index"],
    )
    op.drop_index("ix_document_chunks_attachment_id", table_name="document_chunks")
    op.drop_constraint(
        "fk_document_chunks_attachment_id", "document_chunks", type_="foreignkey"
    )
    op.drop_column("document_chunks", "attachment_id")

    op.drop_index("ix_document_sections_attachment_id", table_name="document_sections")
    op.drop_constraint(
        "fk_document_sections_attachment_id", "document_sections", type_="foreignkey"
    )
    op.drop_column("document_sections", "attachment_id")

    op.drop_index("ix_papers_active_attachment_id", table_name="papers")
    op.drop_constraint("fk_papers_active_attachment_id", "papers", type_="foreignkey")
    op.drop_column("papers", "active_attachment_id")
    op.drop_column("attachments", "processing_token")
