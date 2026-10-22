from app.models import Author, Paper, PaperAuthor, Tag
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_paper_relationships_round_trip(db: Session) -> None:
    paper = Paper(
        title="A test paper",
        tags=[Tag(name="methods")],
        author_links=[
            PaperAuthor(
                author=Author(
                    first_name="Ada", last_name="Lovelace", normalized_name="ada lovelace"
                ),
                author_order=0,
            )
        ],
    )
    db.add(paper)
    db.commit()
    loaded = db.scalar(select(Paper).where(Paper.id == paper.id))
    assert loaded is not None
    assert loaded.authors[0].last_name == "Lovelace"
    assert loaded.tags[0].name == "methods"
