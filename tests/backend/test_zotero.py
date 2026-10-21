from app.services.zotero import map_item_fields, normalize_author


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
