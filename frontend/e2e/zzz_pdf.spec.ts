import { test, expect } from "@playwright/test";
test("PDF.js renders, searches, navigates and restores zoom without remote assets", async ({
  page,
}) => {
  const errors: string[] = [],
    remote: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("request", (r) => {
    if (
      /^https?:/.test(r.url()) &&
      !r.url().startsWith("http://127.0.0.1:8765/")
    )
      remote.push(r.url());
  });
  await page.goto("/app/?file_key=fixture-2.pdf");
  await expect(page.locator(".pdfViewer canvas").first()).toBeVisible();
  await expect(page.locator(".textLayer").first()).toContainText("Exploring");
  await page.getByRole("button", { name: "下一页", exact: true }).click();
  await expect(page.getByLabel("PDF 页码")).toHaveValue("2");
  await expect(
    page.getByRole("button", { name: "下一页", exact: true }),
  ).toBeDisabled();
  await page.getByLabel("PDF 页码").fill("999");
  await page.getByLabel("PDF 页码").press("Tab");
  await expect(page.getByLabel("PDF 页码")).toHaveValue("2");
  await page.getByLabel("PDF 缩放").selectOption("1.25");
  await page.reload();
  await expect(page.locator(".pdfViewer canvas").first()).toBeVisible();
  await expect(page.getByLabel("PDF 页码")).toHaveValue("2");
  await expect(page.getByLabel("PDF 缩放")).toHaveValue("1.25");
  await page.getByLabel("搜索 PDF 原文").fill("page 1");
  await expect(page.locator(".pdf-find [role=status]")).toHaveText("1 / 1");
  await expect(page.getByLabel("PDF 页码")).toHaveValue("1");
  await expect(page.locator(".textLayer .highlight").first()).toBeVisible();
  await page.getByLabel("搜索 PDF 原文").fill("missing-query-123");
  await expect(page.locator(".pdf-find [role=status]")).toHaveText("未找到");
  await page.getByLabel("原文对照", { exact: true }).uncheck();
  await expect(page.locator(".pdf-reader")).toHaveCount(0);
  await page.getByLabel("原文对照", { exact: true }).check();
  await expect(page.locator(".pdfViewer canvas").first()).toBeVisible();
  await page.screenshot({ path: "test-results/pdfjs-reader.png" });
  expect(errors).toEqual([]);
  expect(remote).toEqual([]);
});
test("invalid PDF shows a recoverable error and keeps reading content available", async ({
  page,
}) => {
  await page.route("**/papers/fixture-2.pdf", (route) =>
    route.fulfill({ contentType: "application/pdf", body: "invalid PDF" }),
  );
  await page.goto("/app/?file_key=fixture-2.pdf");
  await expect(page.locator(".pdf-reader [role=alert]")).toContainText(
    "无法读取 PDF",
  );
  await expect(
    page.getByText("Verified cached summary", { exact: true }),
  ).toBeVisible();
});
