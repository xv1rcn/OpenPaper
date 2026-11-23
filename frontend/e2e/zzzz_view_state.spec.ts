import { test, expect } from "./fixtures";

test("reader and library state survive a fresh browser context", async ({ browser, request }) => {
  const baseURL = "http://127.0.0.1:8765";
  const values: Record<string, string> = {
    "openpaper-library-layout": "list",
    "openpaper-reader-fixture-2.pdf": JSON.stringify({ page: 2, width: 60, showPdf: true }),
    "openpaper-reader-fixture-2.pdf-zoom": "1.25",
  };
  for (const [key, value] of Object.entries(values)) {
    expect((await request.post("/api/view-state", { data: { key, value }, headers: { "X-OpenPaper-Request": "1" } })).ok()).toBeTruthy();
  }
  const context = await browser.newContext({ baseURL });
  try {
    const page = await context.newPage();
    await page.goto("/app/?file_key=fixture-2.pdf");
    await expect(page.locator(".pdfViewer canvas").first()).toBeVisible();
    await expect(page.getByLabel("PDF 页码")).toHaveValue("2");
    await expect(page.locator(".pdf-controls select")).toHaveValue("1.25");
    await page.locator(".pdf-controls select").selectOption("1.5");
    await expect.poll(async () => (await (await request.get("/api/view-state")).json()).values["openpaper-reader-fixture-2.pdf-zoom"]).toBe("1.5");
    await page.goto("/app/");
    await expect(page.getByRole("button", { name: "列表视图" })).toHaveAttribute("aria-pressed", "true");
    expect(await page.evaluate(() => localStorage.length)).toBe(0);
  } finally { await context.close(); }
  const restored = await browser.newContext({ baseURL });
  try {
    const page = await restored.newPage();
    await page.goto("/app/?file_key=fixture-2.pdf");
    await expect(page.locator(".pdf-controls select")).toHaveValue("1.5");
  } finally { await restored.close(); }
});
