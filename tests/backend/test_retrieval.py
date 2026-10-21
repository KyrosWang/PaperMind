from app.models import DocumentChunk, DocumentSection, Paper
from app.services.retrieval import retrieve
from sqlalchemy.orm import Session


def test_lexical_retrieval_is_scoped_to_paper(db: Session) -> None:
    paper = Paper(title="Target")
    other = Paper(title="Other")
    db.add_all([paper, other])
    db.flush()
    section = DocumentSection(paper_id=paper.id, heading="Results", section_order=0)
    other_section = DocumentSection(paper_id=other.id, heading="Results", section_order=0)
    db.add_all([section, other_section])
    db.flush()
    db.add_all(
        [
            DocumentChunk(
                paper_id=paper.id,
                section_id=section.id,
                text="Mice improved with treatment",
                chunk_index=0,
                token_count=5,
            ),
            DocumentChunk(
                paper_id=paper.id,
                section_id=section.id,
                text="Unrelated methods",
                chunk_index=1,
                token_count=2,
            ),
            DocumentChunk(
                paper_id=other.id,
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
