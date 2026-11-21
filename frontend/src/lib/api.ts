import type { Paper, RecycleItem } from "./types";
async function request<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(
    path,
    body === undefined
      ? { cache: "no-store" }
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-OpenPaper-Request": "1",
          },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json().catch(() => null);
  if (!response.ok || !data?.ok)
    throw new Error(data?.error || `请求失败 (${response.status})`);
  return data as T;
}
export const api = {
  library: () => request<{ papers: Paper[] }>("/api/library"),
  recycle: () => request<{ items: RecycleItem[] }>("/api/recycle-list"),
  update: (
    file_key: string,
    fields: Partial<Pick<Paper, "title" | "tags" | "read" | "notes">>,
  ) => request("/api/update-paper", { file_key, fields }),
  remove: (file_key: string) => request("/api/delete-paper", { file_key }),
  restore: (id: string) => request("/api/recycle-restore", { id }),
};
export function normalizePaper(raw: Partial<Paper>): Paper {
  return {
    file_key: String(raw.file_key || ""),
    title: String(raw.title || "未命名论文"),
    authors: typeof raw.authors === "string" ? raw.authors : "",
    year: String(raw.year || ""),
    venue: String(raw.venue || ""),
    tags: Array.isArray(raw.tags)
      ? raw.tags.filter((t) => typeof t === "string")
      : [],
    pdf: String(raw.pdf || ""),
    read: raw.read === true,
    notes: String(raw.notes || ""),
    added_at: String(raw.added_at || ""),
  };
}
export const legacyOrigin = import.meta.env.DEV ? "http://127.0.0.1:8001" : "";
export const readerUrl = (paper: Paper) =>
  `${legacyOrigin}/quick-reading.html?file_key=${encodeURIComponent(paper.file_key)}`;
export function pdfUrl(paper: Paper): string | null {
  const parts = paper.pdf.split("/");
  if (
    parts[0] !== "papers" ||
    parts.some((p) => !p || p === "." || p === ".." || p.includes("\\")) ||
    !paper.pdf.toLowerCase().endsWith(".pdf")
  )
    return null;
  return "/" + parts.map(encodeURIComponent).join("/");
}
