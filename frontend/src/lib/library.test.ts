import { describe, it, expect } from "vitest";
import { filterPapers, parseTags } from "./library";
import { normalizePaper, pdfUrl } from "./api";
const papers = [
  normalizePaper({
    file_key: "a",
    title: "OOD Detection",
    authors: "Alice",
    tags: ["Vision"],
    read: false,
    year: "2024",
  }),
  normalizePaper({
    file_key: "b",
    title: "Language Models",
    authors: "Bob",
    tags: ["NLP"],
    read: true,
    year: "2025",
  }),
];
describe("library queries", () => {
  it("combines terms, collection and tag without modifying the source", () => {
    expect(
      filterPapers(papers, "alice vision", "unread", "Vision", "title").map(
        (p) => p.file_key,
      ),
    ).toEqual(["a"]);
    expect(filterPapers(papers, "alice", "read", "", "title")).toEqual([]);
    expect(
      filterPapers(papers, "", "all", "", "year").map((p) => p.file_key),
    ).toEqual(["b", "a"]);
    expect(papers[0].file_key).toBe("a");
  });
  it("deduplicates Chinese and English tag separators", () =>
    expect(parseTags(" OOD，Vision,OOD\n NLP ")).toEqual([
      "OOD",
      "Vision",
      "NLP",
    ]));
  it("does not double-encode scanner document URLs", () => {
    expect(
      pdfUrl(
        normalizePaper({ pdf: "papers/imported/%E8%AE%BA%E6%96%87%20a.pdf" }),
      ),
    ).toBe("/papers/imported/%E8%AE%BA%E6%96%87%20a.pdf");
    expect(
      pdfUrl(normalizePaper({ pdf: "papers/%2e%2e/secret.pdf" })),
    ).toBeNull();
    expect(
      pdfUrl(normalizePaper({ pdf: "papers/sub%2fsecret.pdf" })),
    ).toBeNull();
  });
  it("rejects external and traversal document URLs", () => {
    for (const pdf of [
      "https://evil.example/x.pdf",
      "papers/../secret.pdf",
      "papers/\\secret.pdf",
    ])
      expect(pdfUrl(normalizePaper({ pdf }))).toBeNull();
    expect(pdfUrl(normalizePaper({ pdf: "papers/你好 a.pdf" }))).toBe(
      "/papers/%E4%BD%A0%E5%A5%BD%20a.pdf",
    );
  });
});
