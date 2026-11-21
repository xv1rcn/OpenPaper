import type { Paper } from "./types";
export function libraryStatistics(papers: Paper[]) {
  const days = new Map<string, number>(),
    weeks = new Map<string, number>();
  const tags = new Map<
    string,
    { total: number; read: number; years: Record<string, number> }
  >();
  const months = new Map<string, { added: number; read: number }>();
  for (const paper of papers) {
    for (const tag of new Set(paper.tags)) {
      const entry = tags.get(tag) || { total: 0, read: 0, years: {} };
      entry.total++;
      entry.read += Number(paper.read);
      const year = paper.year || "未知";
      entry.years[year] = (entry.years[year] || 0) + 1;
      tags.set(tag, entry);
    }
    const day = paper.added_at.slice(0, 10);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) continue;
    const date = new Date(day + "T00:00:00Z");
    if (
      !Number.isFinite(date.getTime()) ||
      date.toISOString().slice(0, 10) !== day
    )
      continue;
    days.set(day, (days.get(day) || 0) + 1);
    date.setUTCDate(date.getUTCDate() - ((date.getUTCDay() + 6) % 7));
    const week = date.toISOString().slice(0, 10);
    weeks.set(week, (weeks.get(week) || 0) + 1);
    const month = day.slice(0, 7),
      entry = months.get(month) || { added: 0, read: 0 };
    entry.added++;
    entry.read += Number(paper.read);
    months.set(month, entry);
  }
  let cumulative = 0,
    cumulativeRead = 0;
  return {
    days: [...days].sort(([a], [b]) => a.localeCompare(b)),
    weeks: [...weeks].sort(([a], [b]) => a.localeCompare(b)),
    months: [...months]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([month, value]) => ({
        month,
        ...value,
        cumulative: (cumulative += value.added),
        cumulativeRead: (cumulativeRead += value.read),
      })),
    tags: [...tags].sort(([a], [b]) => a.localeCompare(b)),
    years: [...new Set(papers.map((p) => p.year || "未知"))].sort(),
  };
}
