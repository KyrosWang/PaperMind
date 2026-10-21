# Future Zotero Desktop companion

The future companion should run only on the machine where Zotero Desktop is running. It must query
the Zotero Local API on loopback, never expose that API to the LAN, and upload missing PDFs over an
authenticated PaperMind connection.

Proposed loop:

1. Read top-level items and their PDF attachment metadata from the local API.
2. Match the parent Zotero item key to `Paper.zotero_item_key` (sync metadata first if absent).
3. Hash the local PDF and compare with a small durable manifest of uploaded hashes.
4. Upload unknown hashes to `POST /api/papers/{id}/attachments`.
5. Record the server attachment ID, hash, local attachment key, and successful timestamp.
6. Retry network failures with bounded exponential backoff; never delete either local copy.

The helper should use platform-native Zotero storage discovery only as a fallback; the Local API is
the preferred boundary. It should be a separate small package so the server never needs access to
desktop paths.

