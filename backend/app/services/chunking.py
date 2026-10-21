import re
from dataclasses import dataclass


@dataclass(slots=True)
class Paragraph:
    text: str
    page_start: int | None = None
    page_end: int | None = None


@dataclass(slots=True)
class Chunk:
    text: str
    token_count: int
    page_start: int | None
    page_end: int | None


def estimate_tokens(text: str) -> int:
    """Portable token estimate; providers may tokenize more precisely later."""
    return max(1, len(re.findall(r"\w+|[^\w\s]", text)))


def _tail_words(text: str, desired_tokens: int) -> str:
    if desired_tokens <= 0:
        return ""
    words = text.split()
    ratio = min(len(words), max(1, int(desired_tokens * 0.75)))
    return " ".join(words[-ratio:])


def chunk_paragraphs(
    paragraphs: list[Paragraph], target_tokens: int = 500, overlap_tokens: int = 60
) -> list[Chunk]:
    """Create section-local chunks without splitting paragraphs unless one is oversized."""
    if target_tokens <= 0 or overlap_tokens < 0 or overlap_tokens >= target_tokens:
        raise ValueError("Chunk target must be positive and overlap smaller than target")

    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0
    page_start: int | None = None
    page_end: int | None = None

    def flush() -> None:
        nonlocal current, current_tokens, page_start, page_end
        if not current:
            return
        text = "\n\n".join(current).strip()
        chunks.append(Chunk(text, estimate_tokens(text), page_start, page_end))
        overlap = _tail_words(text, overlap_tokens)
        current = [overlap] if overlap else []
        current_tokens = estimate_tokens(overlap) if overlap else 0
        page_start = page_end if overlap else None

    for paragraph in paragraphs:
        text = " ".join(paragraph.text.split()).strip()
        if not text:
            continue
        token_count = estimate_tokens(text)
        if current and current_tokens + token_count > target_tokens:
            flush()
        if token_count > target_tokens:
            words = text.split()
            word_target = max(1, int(target_tokens * 0.75))
            for offset in range(0, len(words), max(1, word_target - int(overlap_tokens * 0.75))):
                part = " ".join(words[offset : offset + word_target])
                chunks.append(
                    Chunk(part, estimate_tokens(part), paragraph.page_start, paragraph.page_end)
                )
            current = []
            current_tokens = 0
            page_start = None
            page_end = None
            continue
        current.append(text)
        current_tokens += token_count
        page_start = page_start or paragraph.page_start
        page_end = paragraph.page_end or paragraph.page_start or page_end
    flush()
    return chunks
