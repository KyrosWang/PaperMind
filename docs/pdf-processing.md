# PDF processing

Upload a PDF from a paper page or with multipart form data at
`POST /api/papers/{paper_id}/attachments`. The API accepts PDF-like MIME types, enforces
`MAX_UPLOAD_MB`, verifies the `%PDF-` signature, calculates SHA-256 while streaming to a spooled
temporary file, rejects duplicate hashes for a paper, and saves to:

```text
DATA_ROOT/papers/<paper_uuid>/<attachment_uuid>/original.pdf
DATA_ROOT/papers/<paper_uuid>/parsed-<attachment_uuid>.tei.xml
```

The first upload becomes active automatically. Later uploads remain inactive unless sent with
`?replace_active=true`; an existing attachment can be explicitly selected with
`POST /api/papers/{paper_id}/attachments/{attachment_id}/activate`. Activating or replacing a PDF
enqueues fresh processing.

The API enqueues only the active attachment ID. The worker resolves the storage path, sends the PDF to
GROBID, stores TEI, extracts abstract/body sections/reference entries and best-effort page markers,
then chunks within each section. Paragraphs are accumulated toward `CHUNK_TARGET_TOKENS`; limited
tail overlap is controlled by `CHUNK_OVERLAP_TOKENS`. An oversized paragraph is split by words.

Embeddings are written in batches. Parsed rows are keyed by attachment, and each task carries a
processing token. Superseded or inactive tasks stop before they can replace current content;
retries idempotently rebuild only their target attachment. Any parsing or embedding failure marks
the current processing run `failed` and records a safe error summary.
Scanned documents are not OCR'd in V1. GROBID page markers are not guaranteed for every source,
so evidence can have a section without a page.

