# PDF processing

Upload a PDF from a paper page or with multipart form data at
`POST /api/papers/{paper_id}/attachments`. The API accepts PDF-like MIME types, enforces
`MAX_UPLOAD_MB`, verifies the `%PDF-` signature, calculates SHA-256 while streaming to a spooled
temporary file, rejects duplicate hashes for a paper, and saves to:

```text
DATA_ROOT/papers/<paper_uuid>/<attachment_uuid>/original.pdf
DATA_ROOT/papers/<paper_uuid>/parsed-<attachment_uuid>.tei.xml
```

The API enqueues only the attachment ID. The worker resolves the storage path, sends the PDF to
GROBID, stores TEI, extracts abstract/body sections/reference entries and best-effort page markers,
then chunks within each section. Paragraphs are accumulated toward `CHUNK_TARGET_TOKENS`; limited
tail overlap is controlled by `CHUNK_OVERLAP_TOKENS`. An oversized paragraph is split by words.

Embeddings are written in batches. Any parsing or embedding failure marks the attachment `failed`
and records a safe error summary. Retrying the Celery task rebuilds sections transactionally.
Scanned documents are not OCR'd in V1. GROBID page markers are not guaranteed for every source,
so evidence can have a section without a page.

