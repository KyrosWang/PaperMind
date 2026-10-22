export type ProcessingStatus = "pending" | "parsing" | "embedding" | "ready" | "failed";

export interface Author {
  first_name: string | null;
  last_name: string | null;
  normalized_name: string;
}

export interface Attachment {
  id: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  checksum: string;
  processing_status: ProcessingStatus;
  processing_error: string | null;
}

export interface Section {
  id: string;
  heading: string | null;
  section_type: string | null;
  section_order: number;
  page_start: number | null;
  page_end: number | null;
}

export interface Paper {
  id: string;
  zotero_item_key: string | null;
  title: string;
  abstract: string | null;
  doi: string | null;
  journal: string | null;
  publication_year: number | null;
  url: string | null;
  active_attachment_id: string | null;
  authors: Author[];
  attachments: Attachment[];
  sections?: Section[];
}

export interface Citation {
  evidence_index: number;
  chunk_id: string;
  section: string | null;
  page: number | null;
  excerpt: string;
  relevance_score: number;
}

export interface ChatReply {
  conversation_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
}

export interface LibraryFacets {
  collections: Array<{ id: string; name: string }>;
  tags: Array<{ id: string; name: string }>;
}

