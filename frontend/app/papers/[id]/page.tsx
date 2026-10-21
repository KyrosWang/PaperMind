import { notFound } from "next/navigation";
import { PaperWorkspace } from "@/components/PaperWorkspace";
import { apiJson } from "@/lib/api";
import type { Paper } from "@/lib/types";

export default async function PaperPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let paper: Paper;
  try {
    paper = await apiJson<Paper>(`/papers/${id}`, { cache: "no-store" });
  } catch {
    notFound();
  }
  return <PaperWorkspace initialPaper={paper} />;
}

