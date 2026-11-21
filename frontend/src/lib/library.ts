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
    .sort((a, b) => {
      const title = a.title.localeCompare(b.title, "zh-CN");
      const venue = a.venue.localeCompare(b.venue, "zh-CN");
      const year = (Number(b.year) || 0) - (Number(a.year) || 0);
      const date = b.added_at.localeCompare(a.added_at);
      return (
        {
          title,
          "title-desc": -title,
          venue,
          "venue-desc": -venue,
          year,
          "year-asc": -year,
          recent: date,
          oldest: -date,
        }[sort] || a.file_key.localeCompare(b.file_key)
      );
    });
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
