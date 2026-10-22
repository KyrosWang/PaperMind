# Data model

`Paper` caches Zotero-controlled metadata and uses `zotero_item_key` as its external identity.
`zotero_deleted_at` is a soft marker: deleting an item in Zotero removes it from the normal library
view without deleting locally owned PDFs or conversations.

`PaperAuthor` is an explicit ordered association. Display names are not globally unique identities,
so two people named "Wei Wang" may have separate `Author` rows. Tags and collections remain
many-to-many entities. Collections support a self-referencing parent. `ZoteroSyncState` stores the
last successfully committed library version.

`Attachment` owns the immutable checksum, relative storage path, and processing state. A unique
paper/checksum constraint prevents duplicate attachment rows. `Paper.active_attachment_id`
selects the one PDF used for reading, parsing, retrieval, and chat. Sections and chunks carry both
paper and attachment IDs, so reprocessing one attachment cannot erase another attachment's parsed
representation. `DocumentSection` preserves TEI structure; `DocumentChunk` has page range, token
estimate, text, and a pgvector `vector` column. The vector column is not dimension-constrained in
the schema so an embedding migration is not coupled to one vendor. Production should use one
configured dimension at a time; changing models requires re-embedding before adding an ANN index.

`Conversation` contains ordered `Message` records. `RetrievedEvidence` records every numbered
chunk supplied to an assistant request. `CitationEvidence` records only indices the structured LLM
response actually cited, after server-side range validation.

The initial migration creates pgvector, relational constraints, common lookup indexes, and a GIN
full-text index over chunk text. Exact nearest-neighbor search is appropriate for personal V1
libraries; an HNSW index can be added once corpus size and embedding dimension are known.

