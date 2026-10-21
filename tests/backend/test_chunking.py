from app.services.chunking import Paragraph, chunk_paragraphs


def test_chunking_preserves_pages_and_overlap() -> None:
    paragraphs = [
        Paragraph("alpha " * 60, 1, 1),
        Paragraph("beta " * 60, 2, 2),
        Paragraph("gamma " * 60, 3, 3),
    ]
    chunks = chunk_paragraphs(paragraphs, target_tokens=100, overlap_tokens=10)
    assert len(chunks) >= 3
    assert chunks[0].page_start == 1
    assert chunks[-1].page_end == 3
    assert "alpha" in chunks[1].text


def test_chunking_rejects_invalid_overlap() -> None:
    try:
        chunk_paragraphs([], target_tokens=100, overlap_tokens=100)
    except ValueError as exc:
        assert "overlap" in str(exc)
    else:
        raise AssertionError("Expected invalid settings to fail")
