"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { apiJson } from "@/lib/api";
import type { LibraryFacets, Paper } from "@/lib/types";

function status(paper: Paper): string {
  if (!paper.attachments.length) return "No PDF";
  return paper.attachments[0].processing_status;
}

export default function LibraryPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [query, setQuery] = useState("");
  const [collection, setCollection] = useState("");
  const [tag, setTag] = useState("");
  const [facets, setFacets] = useState<LibraryFacets>({ collections: [], tags: [] });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load(search = "", collectionId = collection, tagId = tag) {
    setLoading(true);
    setError(null);
    try {
      const parameters = new URLSearchParams();
      if (search) parameters.set("q", search);
      if (collectionId) parameters.set("collection", collectionId);
      if (tagId) parameters.set("tag", tagId);
      setPapers(await apiJson<Paper[]>(`/papers${parameters.size ? `?${parameters}` : ""}`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load the library");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    void Promise.all([apiJson<Paper[]>("/papers"), apiJson<LibraryFacets>("/papers/facets")])
      .then(([items, availableFacets]) => { if (active) { setPapers(items); setFacets(availableFacets); } })
      .catch((reason: unknown) => { if (active) setError(reason instanceof Error ? reason.message : "Unable to load the library"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);
  function submit(event: FormEvent) { event.preventDefault(); void load(query); }

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-moss">Library</p>
          <h1 className="font-serif text-4xl font-semibold">Your scientific record</h1>
          <p className="mt-2 text-sm text-black/55">Metadata from Zotero. PDFs and reading history live here.</p>
        </div>
        <form onSubmit={submit} className="grid w-full max-w-2xl grid-cols-[1fr_auto_auto_auto] gap-2">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search title, author, DOI, abstract, journal…"
            className="min-w-0 flex-1 rounded-xl border-black/15 bg-white px-4 py-2.5 text-sm focus:border-moss focus:ring-moss"
          />
          <select aria-label="Collection" value={collection} onChange={(event) => { setCollection(event.target.value); void load(query, event.target.value, tag); }} className="rounded-xl border-black/15 bg-white py-2.5 text-sm focus:border-moss focus:ring-moss">
            <option value="">All collections</option>
            {facets.collections.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <select aria-label="Tag" value={tag} onChange={(event) => { setTag(event.target.value); void load(query, collection, event.target.value); }} className="rounded-xl border-black/15 bg-white py-2.5 text-sm focus:border-moss focus:ring-moss">
            <option value="">All tags</option>
            {facets.tags.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
          <button className="rounded-xl bg-ink px-5 py-2.5 text-sm font-medium text-white hover:bg-moss">Search</button>
        </form>
      </div>

      {error && <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</div>}
      {loading ? (
        <p className="py-20 text-center text-black/50">Loading library…</p>
      ) : papers.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-black/20 p-16 text-center">
          <h2 className="font-serif text-2xl">No papers yet</h2>
          <p className="mt-2 text-sm text-black/55">Run a Zotero sync or seed demo metadata from the CLI.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {papers.map((paper) => (
            <Link key={paper.id} href={`/papers/${paper.id}`} className="group rounded-2xl border border-black/10 bg-white p-5 shadow-lift hover:border-moss/40">
              <div className="mb-8 flex justify-between gap-3">
                <span className="text-xs font-medium uppercase tracking-wider text-moss">{paper.journal ?? "Unpublished"}</span>
                <span className="text-xs text-black/40">{paper.publication_year ?? "—"}</span>
              </div>
              <h2 className="font-serif text-xl font-semibold leading-snug group-hover:text-moss">{paper.title}</h2>
              <p className="mt-3 text-sm text-black/55">{paper.authors[0]?.normalized_name ?? "Unknown author"}{paper.authors.length > 1 ? " et al." : ""}</p>
              <div className="mt-6 flex items-center justify-between border-t border-black/10 pt-4 text-xs">
                <span className="capitalize text-black/50">{status(paper)}</span>
                <span className="font-medium text-moss">Open paper →</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}

