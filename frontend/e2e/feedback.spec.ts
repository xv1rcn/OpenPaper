import { test, expect } from "./fixtures";

test("missing speedread is an empty state; storage errors remain visible", async ({
  page,
}) => {
  await page.route("**/api/speedread-cache?*", (r) =>
    r.fulfill({
      status: 404,
      json: {
        ok: false,
        code: "speedread_not_generated",
        error: "尚未生成速读",
      },
    }),
  );
  await page.goto("/app/?file_key=fixture-0.pdf");
  await expect(
    page.getByRole("heading", { name: "尚未生成速读" }),
  ).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
  await page.unroute("**/api/speedread-cache?*");
  await page.route("**/api/speedread-cache?*", (r) =>
    r.fulfill({ status: 500, json: { ok: false, error: "缓存读取失败" } }),
  );
  await page.reload();
  await expect(page.getByRole("alert")).toContainText("缓存读取失败");
  await expect(page.getByRole("heading", { name: "尚未生成速读" })).toHaveCount(
    0,
  );
});

test("partial save warnings remain visible and do not claim full success", async ({
  page,
}) => {
  await page.goto("/app/");
  await page.route("**/api/settings", async (route) => {
    const data = {
      ok: true,
      revision: "test",
      hasCredential: true,
      provider: {
        apiBaseUrl: "https://example.invalid",
        model: "test",
        timeoutSec: 120,
        contextWindow: 0,
        maxOutputTokens: 0,
      },
    };
    await route.fulfill({
      json:
        route.request().method() === "POST"
          ? { ...data, warning: "新配置已保存，但旧凭据未能清理" }
          : data,
    });
  });
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await page.getByLabel("模型名称", { exact: true }).fill("new-model");
  await page.getByRole("button", { name: "保存", exact: true }).click();
  await expect(page.locator(".feedback-warning")).toContainText(
    "旧凭据未能清理",
  );
  await expect(page.locator(".feedback-success")).toHaveCount(0);
  await page.waitForTimeout(4500);
  await expect(page.locator(".feedback-warning")).toBeVisible();
});

test("technical modules read as prose and source links still navigate the PDF", async ({
  page,
}) => {
  await page.goto("/app/?file_key=fixture-2.pdf");
  const section = page.locator("#technical_detail_read");
  await section.scrollIntoViewIfNeeded();
  await expect(
    section.getByRole("heading", { name: "Module A", exact: true }),
  ).toBeVisible();
  await expect(section).toContainText("Controlled fixture");
  await expect(section.locator(".reading-record")).toHaveCount(0);
  await section.getByRole("button", { name: "第 2 页", exact: true }).click();
  await expect(page.getByLabel("PDF 页码", { exact: true })).toHaveValue("2");
});
