# Data model

`Paper` caches Zotero-controlled metadata and uses `zotero_item_key` as its external identity.
`zotero_deleted_at` is a soft marker: deleting an item in Zotero removes it from the normal library
view without deleting locally owned PDFs or conversations.

Authors, tags, and collections are normalized entities with many-to-many paper associations.
Collections support a self-referencing parent. `ZoteroSyncState` stores the last successfully
committed library version.

`Attachment` owns the immutable checksum, relative storage path, and processing state. A unique
paper/checksum constraint prevents duplicate attachment rows. `DocumentSection` preserves TEI
structure; `DocumentChunk` belongs to a paper and optionally a section, with page range, token
estimate, text, and a pgvector `vector` column. The vector column is not dimension-constrained in
the schema so an embedding migration is not coupled to one vendor. Production should use one
configured dimension at a time; changing models requires re-embedding before adding an ANN index.

`Conversation` contains ordered `Message` records. `CitationEvidence` links assistant messages to
the exact retrieved chunks and stores the fused relevance score.

The initial migration creates pgvector, relational constraints, common lookup indexes, and a GIN
full-text index over chunk text. Exact nearest-neighbor search is appropriate for personal V1
libraries; an HNSW index can be added once corpus size and embedding dimension are known.

