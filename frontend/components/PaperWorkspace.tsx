"use client";

import { ChangeEvent, useState } from "react";
import { apiJson } from "@/lib/api";
import type { Attachment, Paper } from "@/lib/types";
import { ChatPanel } from "./ChatPanel";
import { PdfReader } from "./PdfReader";

export function PaperWorkspace({ initialPaper }: { initialPaper: Paper }) {
  const [paper, setPaper] = useState(initialPaper);
  const [page, setPage] = useState(1);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const attachment = paper.attachments.find((item) => item.id === paper.active_attachment_id) ?? null;

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const suffix = paper.active_attachment_id ? "?replace_active=true" : "";
      const created = await apiJson<Attachment>(`/papers/${paper.id}/attachments${suffix}`, { method: "POST", body: form });
      setPaper((value) => ({
        ...value,
        active_attachment_id: created.id,
        attachments: [created, ...value.attachments],
        sections: [],
      }));
    } catch (reason) {
      setUploadError(reason instanceof Error ? reason.message : "Upload failed");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  return (
    <main className="grid h-[calc(100vh-4rem)] min-h-0 grid-cols-1 overflow-hidden xl:grid-cols-[260px_minmax(480px,1fr)_360px]">
      <aside className="hidden min-h-0 overflow-auto border-r border-black/10 bg-paper p-5 xl:block">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-moss">Paper</p>
        <h1 className="mt-3 font-serif text-2xl font-semibold leading-tight">{paper.title}</h1>
        <p className="mt-3 text-sm text-black/55">{paper.authors.map((author) => author.normalized_name).join(", ") || "Unknown author"}</p>
        <dl className="mt-6 space-y-2 text-xs">
          <div><dt className="text-black/40">Published</dt><dd>{paper.publication_year ?? "—"} · {paper.journal ?? "Unknown venue"}</dd></div>
          {paper.doi && <div><dt className="text-black/40">DOI</dt><dd className="break-all">{paper.doi}</dd></div>}
        </dl>
        <div className="mt-6 border-t border-black/10 pt-5">
          <label className="block cursor-pointer rounded-lg border border-moss px-3 py-2 text-center text-xs font-semibold text-moss hover:bg-mist">
            {uploading ? "Uploading…" : attachment ? "Replace active PDF" : "Upload PDF"}
            <input type="file" accept="application/pdf,.pdf" disabled={uploading} onChange={upload} className="hidden" />
          </label>
          {attachment && <p className="mt-2 text-xs capitalize text-black/45">Processing: {attachment.processing_status}</p>}
          {uploadError && <p className="mt-2 text-xs text-red-700">{uploadError}</p>}
        </div>
        <nav className="mt-8 border-t border-black/10 pt-5">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-black/40">Outline</p>
          <div className="space-y-1">
            {paper.sections?.length ? paper.sections.map((section) => (
              <button key={section.id} onClick={() => section.page_start && setPage(section.page_start)} className="block w-full truncate rounded px-2 py-1.5 text-left text-xs hover:bg-mist">
                {section.heading ?? section.section_type ?? "Untitled section"}
              </button>
            )) : <p className="text-xs text-black/40">Available after processing.</p>}
          </div>
        </nav>
      </aside>
      <PdfReader paperId={paper.id} attachmentId={attachment?.id ?? null} requestedPage={page} onPageChange={setPage} />
      <div className="hidden min-h-0 border-l border-black/10 xl:block"><ChatPanel paperId={paper.id} onEvidence={setPage} /></div>
    </main>
  );
}

