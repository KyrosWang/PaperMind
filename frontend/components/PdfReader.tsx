"use client";

import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import { apiFetch } from "@/lib/api";

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.min.mjs",
  import.meta.url,
).toString();

interface PdfReaderProps {
  paperId: string;
  attachmentId: string | null;
  requestedPage: number;
  onPageChange: (page: number) => void;
}

export function PdfReader({ paperId, attachmentId, requestedPage, onPageChange }: PdfReaderProps) {
  const [source, setSource] = useState<string | null>(null);
  const [pages, setPages] = useState(0);
  const [scale, setScale] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!attachmentId) return;
    let url: string | null = null;
    void apiFetch(`/papers/${paperId}/attachments/${attachmentId}/file`)
      .then((response) => {
        if (!response.ok) throw new Error("Unable to load PDF");
        return response.blob();
      })
      .then((blob) => {
        url = URL.createObjectURL(blob);
        setSource(url);
      })
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Unable to load PDF"));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [paperId, attachmentId]);

  const page = Math.min(Math.max(requestedPage, 1), pages || 1);
  if (!attachmentId) {
    return <div className="grid h-full place-items-center text-sm text-black/45">Upload a PDF to begin reading.</div>;
  }

  return (
    <div ref={container} className="flex h-full min-h-0 flex-col bg-[#e8e6df]">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-black/10 bg-white px-3 text-sm">
        <div className="flex items-center gap-2">
          <button aria-label="Previous page" disabled={page <= 1} onClick={() => onPageChange(page - 1)} className="rounded border px-2 py-1 disabled:opacity-30">←</button>
          <span>Page <strong>{page}</strong> / {pages || "—"}</span>
          <button aria-label="Next page" disabled={page >= pages} onClick={() => onPageChange(page + 1)} className="rounded border px-2 py-1 disabled:opacity-30">→</button>
        </div>
        <div className="flex items-center gap-2">
          <button aria-label="Zoom out" onClick={() => setScale((value) => Math.max(0.6, value - 0.15))} className="rounded border px-2 py-1">−</button>
          <span className="w-11 text-center text-xs">{Math.round(scale * 100)}%</span>
          <button aria-label="Zoom in" onClick={() => setScale((value) => Math.min(2.5, value + 0.15))} className="rounded border px-2 py-1">+</button>
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-auto p-5">
        {error ? <p className="p-8 text-center text-red-700">{error}</p> : !source ? <p className="p-8 text-center text-black/45">Loading PDF…</p> : (
          <Document file={source} onLoadSuccess={({ numPages }) => setPages(numPages)} onLoadError={(reason) => setError(reason.message)}>
            <Page pageNumber={page} scale={scale} renderAnnotationLayer renderTextLayer />
          </Document>
        )}
      </div>
    </div>
  );
}

