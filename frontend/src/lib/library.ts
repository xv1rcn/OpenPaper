import type { Paper, Collection, Sort } from "./types";
export function filterPapers(
  papers: Paper[],
  query: string,
  collection: Collection,
  tag: string,
  sort: Sort,
): Paper[] {
  const terms = query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  return papers
    .filter(
      (p) =>
        (!tag || p.tags.includes(tag)) &&
        (collection !== "read" || p.read) &&
        (collection !== "unread" || !p.read) &&
        terms.every((term) =>
          [p.title, p.authors, p.venue, p.year, ...p.tags]
            .join(" ")
            .toLocaleLowerCase()
            .includes(term),
        ),
    )
    .sort(
      (a, b) =>
        (sort === "title"
          ? a.title.localeCompare(b.title, "zh-CN")
          : sort === "year"
            ? (Number(b.year) || 0) - (Number(a.year) || 0)
            : b.added_at.localeCompare(a.added_at)) ||
        a.file_key.localeCompare(b.file_key),
    );
}
export function parseTags(text: string) {
  return [
    ...new Set(
      text
        .split(/[,，\n]/)
        .map((s) => s.trim())
        .filter(Boolean),
    ),
  ];
}
