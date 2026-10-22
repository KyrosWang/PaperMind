from app.models import Attachment, DocumentChunk, DocumentSection, Paper
from app.services.grobid import ParsedSection
from app.worker import replace_attachment_content
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _attachment(paper_id, name: str) -> Attachment:
    return Attachment(
        paper_id=paper_id,
        filename="original.pdf",
        original_filename=name,
        storage_path=name,
        checksum=name,
        file_size=10,
    )


def test_reprocessing_replaces_only_target_attachment_and_is_idempotent(db: Session) -> None:
    paper = Paper(title="Two PDFs")
    db.add(paper)
    db.flush()
    active = _attachment(paper.id, "active.pdf")
    inactive = _attachment(paper.id, "inactive.pdf")
    db.add_all([active, inactive])
    db.flush()
    paper.active_attachment_id = active.id

    inactive_section = DocumentSection(
        paper_id=paper.id,
        attachment_id=inactive.id,
        heading="Supplement",
        section_order=0,
    )
    db.add(inactive_section)
    db.flush()
    inactive_chunk = DocumentChunk(
        paper_id=paper.id,
        attachment_id=inactive.id,
        section_id=inactive_section.id,
        text="supplemental text must survive",
        chunk_index=0,
        token_count=4,
    )
    db.add(inactive_chunk)
    db.flush()

    parsed = [ParsedSection("Results", "body", [("new active text", 3)])]
    replace_attachment_content(db, active, parsed)
    db.flush()
    replace_attachment_content(db, active, parsed)
    db.commit()

    assert (
        db.scalar(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.attachment_id == active.id)
        )
        == 1
    )
    surviving = db.scalar(select(DocumentChunk).where(DocumentChunk.attachment_id == inactive.id))
    assert surviving is not None
    assert surviving.text == "supplemental text must survive"
    db.expire_all()
    loaded_paper = db.get(Paper, paper.id)
    assert loaded_paper is not None
    assert {section.attachment_id for section in loaded_paper.sections} == {active.id}
