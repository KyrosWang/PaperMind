from app.models import Attachment, DocumentChunk, DocumentSection, Paper
from app.services.retrieval import retrieve
from sqlalchemy.orm import Session


def test_lexical_retrieval_is_scoped_to_paper(db: Session) -> None:
    paper = Paper(title="Target")
    other = Paper(title="Other")
    db.add_all([paper, other])
    db.flush()
    attachment = Attachment(
        paper_id=paper.id,
        filename="original.pdf",
        original_filename="target.pdf",
        storage_path="target.pdf",
        checksum="target",
        file_size=10,
    )
    inactive = Attachment(
        paper_id=paper.id,
        filename="original.pdf",
        original_filename="inactive.pdf",
        storage_path="inactive.pdf",
        checksum="inactive",
        file_size=10,
    )
    other_attachment = Attachment(
        paper_id=other.id,
        filename="original.pdf",
        original_filename="other.pdf",
        storage_path="other.pdf",
        checksum="other",
        file_size=10,
    )
    db.add_all([attachment, inactive, other_attachment])
    db.flush()
    paper.active_attachment_id = attachment.id
    other.active_attachment_id = other_attachment.id
    section = DocumentSection(
        paper_id=paper.id,
        attachment_id=attachment.id,
        heading="Results",
        section_order=0,
    )
    inactive_section = DocumentSection(
        paper_id=paper.id,
        attachment_id=inactive.id,
        heading="Old results",
        section_order=0,
    )
    other_section = DocumentSection(
        paper_id=other.id,
        attachment_id=other_attachment.id,
        heading="Results",
        section_order=0,
    )
    db.add_all([section, inactive_section, other_section])
    db.flush()
    db.add_all(
        [
            DocumentChunk(
                paper_id=paper.id,
                attachment_id=attachment.id,
                section_id=section.id,
                text="Mice improved with treatment",
                chunk_index=0,
                token_count=5,
            ),
            DocumentChunk(
                paper_id=paper.id,
                attachment_id=attachment.id,
                section_id=section.id,
                text="Unrelated methods",
                chunk_index=1,
                token_count=2,
            ),
            DocumentChunk(
                paper_id=paper.id,
                attachment_id=inactive.id,
                section_id=inactive_section.id,
                text="Mice treatment mice treatment mice treatment",
                chunk_index=0,
                token_count=6,
            ),
            DocumentChunk(
                paper_id=other.id,
                attachment_id=other_attachment.id,
                section_id=other_section.id,
                text="Mice treatment",
                chunk_index=0,
                token_count=2,
            ),
        ]
    )
    db.commit()
    results = retrieve(db, paper.id, "mice treatment", 1, None)
    assert len(results) == 1
    assert results[0].chunk.paper_id == paper.id
    assert "Mice" in results[0].chunk.text
