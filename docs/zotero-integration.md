# Zotero integration

Set `ZOTERO_API_KEY`, `ZOTERO_USER_ID`, and `ZOTERO_LIBRARY_TYPE` (`user` or `group`). The API key
needs read access to the selected library. Trigger sync through:

```bash
curl -X POST -H "X-API-Key: $APP_API_KEY" http://localhost:8000/api/zotero/sync
python -m app.cli zotero-sync
```

PaperMind stores Zotero's library version after a complete transaction. Later syncs pass `since`
to the items, collections, and deleted-object endpoints and page in batches of 100. New and changed
top-level bibliographic items are upserted. Authors, tags, collections, and parent collection links
are reconciled. Author creator order is preserved explicitly, while normalized display names are
not treated as globally unique person identifiers. Attachments, notes, and annotations are ignored
because PDFs belong to PaperMind.

Zotero deletions are soft-applied to papers, preserving local storage and history. A failed request
does not advance the version. V1 is read-only and deliberately contains no Zotero mutation code;
future writes should be added behind a separate service method with version preconditions.

