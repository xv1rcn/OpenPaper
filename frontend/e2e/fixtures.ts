import { test as base, expect } from "@playwright/test";
export { expect };
export const test = base.extend<{ resetViewState: void }>({
  resetViewState: [async ({ request }, use) => {
    const response = await request.get("/api/view-state");
    const { values } = await response.json();
    for (const key of Object.keys(values)) {
      const value = key.endsWith("-zoom") ? "page-width"
        : key.startsWith("openpaper-reader-") ? JSON.stringify({ page: 1, width: 50, showPdf: true })
        : key === "openpaper-grouped" ? "false"
        : key === "openpaper-group-order" ? "[]" : "grid";
      await request.post("/api/view-state", { data: { key, value }, headers: { "X-OpenPaper-Request": "1" } });
    }
    await use();
  }, { auto: true }],
});
