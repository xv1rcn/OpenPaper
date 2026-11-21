import { describe, expect, it } from "vitest";
import { libraryStatistics } from "./statistics";
import { normalizePaper } from "./api";
describe("library statistics", () => {
  it("uses Monday weeks across year boundaries and ignores invalid dates", () => {
    const data = libraryStatistics([
      normalizePaper({
        added_at: "2025-12-31",
        tags: ["A", "A"],
        year: "2025",
        read: true,
      }),
      normalizePaper({
        added_at: "2026-01-01",
        tags: ["A", "B"],
        year: "2026",
      }),
      normalizePaper({ added_at: "2026-02-30", tags: ["B"], year: "2026" }),
    ]);
    expect(data.weeks).toEqual([["2025-12-29", 2]]);
    expect(
      data.months.map((r) => [r.month, r.cumulative, r.cumulativeRead]),
    ).toEqual([
      ["2025-12", 1, 1],
      ["2026-01", 2, 1],
    ]);
    expect(data.tags[0]).toEqual([
      "A",
      { total: 2, read: 1, years: { "2025": 1, "2026": 1 } },
    ]);
  });
});
