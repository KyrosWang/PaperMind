from app.models import Paper
from app.services.zotero import _sync_authors, map_item_fields, normalize_author
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_zotero_metadata_mapping() -> None:
    payload = {
        "key": "ABC123",
        "version": 42,
        "data": {
            "key": "ABC123",
            "version": 42,
            "title": "Structured science",
            "abstractNote": "An abstract",
            "DOI": "10.1000/example",
            "date": "2024-03-01",
            "publicationTitle": "Journal of Tests",
            "extra": "PMID: 123456\narXiv: 2401.12345",
            "dateAdded": "2024-03-02T12:00:00Z",
        },
    }
    result = map_item_fields(payload)
    assert result["title"] == "Structured science"
    assert result["publication_year"] == 2024
    assert result["pmid"] == "123456"
    assert result["arxiv_id"] == "2401.12345"
    assert result["zotero_version"] == 42


def test_author_normalization() -> None:
    assert normalize_author("Ada", "Lovelace") == "ada lovelace"


def test_author_order_is_preserved_without_global_name_identity(db: Session) -> None:
    first_paper = Paper(title="First")
    second_paper = Paper(title="Second")
    creators = [
        {"creatorType": "author", "firstName": "Wei", "lastName": "Wang"},
        {"creatorType": "editor", "firstName": "Ed", "lastName": "Itor"},
        {"creatorType": "author", "firstName": "Ada", "lastName": "Lovelace"},
    ]
    _sync_authors(first_paper, creators)
    _sync_authors(
        second_paper,
        [{"creatorType": "author", "firstName": "Wei", "lastName": "Wang"}],
    )
    db.add_all([first_paper, second_paper])
    db.commit()
    db.expire_all()

    loaded = {paper.title: paper for paper in db.scalars(select(Paper).order_by(Paper.title)).all()}
    first_links = loaded["First"].author_links
    second_links = loaded["Second"].author_links
    assert [link.author_order for link in first_links] == [0, 2]
    assert [link.author.normalized_name for link in first_links] == [
        "wei wang",
        "ada lovelace",
    ]
    assert first_links[0].author_id != second_links[0].author_id

    original_ids = [link.author_id for link in first_links]
    _sync_authors(loaded["First"], creators)
    db.commit()
    db.expire_all()
    reloaded = db.scalar(select(Paper).where(Paper.title == "First"))
    assert reloaded is not None
    assert [link.author_id for link in reloaded.author_links] == original_ids
