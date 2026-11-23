import { afterEach, describe, expect, it, vi } from "vitest";
import { loadReading, hasReadingContent } from "./reading";
import { ApiError } from "./api";
afterEach(() => vi.unstubAllGlobals());
function respond(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue({
        ok: status === 200,
        status,
        json: async () => body,
      }),
  );
}
describe("reading feedback states", () => {
  it("treats only an explicit missing-generation code as a normal empty state", async () => {
    respond(404, { ok: false, code: "speedread_not_generated" });
    await expect(loadReading("paper.pdf")).resolves.toEqual({ speed_read: {} });
    respond(404, { ok: false, error: "PDF 不存在" });
    await expect(loadReading("paper.pdf")).rejects.toBeInstanceOf(ApiError);
    respond(500, { ok: false, error: "缓存损坏" });
    await expect(loadReading("paper.pdf")).rejects.toThrow("缓存损坏");
  });
  it("omits empty sections but retains zero, false and explicit evidence limitations", () => {
    expect(hasReadingContent({ summary: "", refs: [] })).toBe(false);
    expect(hasReadingContent({ count: 0, supported: false })).toBe(true);
    expect(hasReadingContent(["论文中未明确说明"])).toBe(true);
  });
});
