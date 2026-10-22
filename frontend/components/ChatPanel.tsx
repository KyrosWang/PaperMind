"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { apiJson } from "@/lib/api";
import type { ChatReply, Citation } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

interface StoredConversation {
  id: string;
  messages: Array<{ role: "user" | "assistant"; content: string }>;
}

export function ChatPanel({ paperId, onEvidence }: { paperId: string; onEvidence: (page: number) => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void apiJson<StoredConversation[]>(`/papers/${paperId}/conversations`)
      .then((items) => {
        if (items[0]) {
          setConversationId(items[0].id);
          setMessages(items[0].messages);
        }
      })
      .catch(() => undefined);
  }, [paperId]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = question.trim();
    if (!value || busy) return;
    setQuestion("");
    setError(null);
    setMessages((current) => [...current, { role: "user", content: value }]);
    setBusy(true);
    try {
      const reply = await apiJson<ChatReply>(`/papers/${paperId}/chat`, {
        method: "POST",
        body: JSON.stringify({ question: value, conversation_id: conversationId }),
      });
      setConversationId(reply.conversation_id);
      setMessages((current) => [...current, { role: "assistant", content: reply.answer, citations: reply.citations }]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The assistant is unavailable");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex h-full min-h-0 flex-col bg-white">
      <div className="border-b border-black/10 px-4 py-3">
        <h2 className="font-serif text-lg font-semibold">Ask this paper</h2>
        <p className="text-xs text-black/45">Answers are grounded in processed sections.</p>
      </div>
      <div className="min-h-0 flex-1 space-y-4 overflow-auto p-4">
        {messages.length === 0 && (
          <div className="rounded-xl bg-paper p-4 text-sm text-black/55">Try “What is the main contribution?” or ask about a result, method, or limitation.</div>
        )}
        {messages.map((message, index) => (
          <div key={index} className={message.role === "user" ? "ml-8 rounded-xl bg-ink p-3 text-sm text-white" : "mr-3 text-sm leading-relaxed"}>
            <p className="whitespace-pre-wrap">{message.content}</p>
            {message.citations && message.citations.length > 0 && (
              <div className="mt-3 space-y-2 border-t border-black/10 pt-3">
                {message.citations.map((citation) => (
                  <button
                    key={citation.chunk_id}
                    disabled={!citation.page}
                    onClick={() => citation.page && onEvidence(citation.page)}
                    className="block w-full rounded-lg border border-black/10 bg-paper p-2 text-left text-xs hover:border-moss disabled:cursor-default"
                  >
                    <span className="font-semibold text-moss">[{citation.evidence_index}] {citation.section ?? "Section"}{citation.page ? ` · page ${citation.page}` : ""}</span>
                    <span className="mt-1 line-clamp-2 block text-black/55">{citation.excerpt}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {busy && <p className="text-sm text-black/45">Reading the evidence…</p>}
        {error && <p className="rounded-lg bg-red-50 p-3 text-xs text-red-800">{error}</p>}
        <div ref={end} />
      </div>
      <form onSubmit={submit} className="border-t border-black/10 p-3">
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }}
          placeholder="Ask a question…"
          rows={3}
          className="w-full resize-none rounded-xl border-black/15 text-sm focus:border-moss focus:ring-moss"
        />
        <div className="mt-2 flex items-center justify-between">
          <span className="text-[11px] text-black/35">Enter to send · Shift+Enter for newline</span>
          <button disabled={busy || !question.trim()} className="rounded-lg bg-moss px-4 py-2 text-xs font-semibold text-white disabled:opacity-40">Ask</button>
        </div>
      </form>
    </section>
  );
}

