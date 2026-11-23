import { test, expect } from "./fixtures";
import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

test("Vue settings persist without returning or storing credentials, and conflict keeps drafts", async ({
  page,
}) => {
  await page.goto("/app/");
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "保存配置", exact: true }),
  ).toBeEnabled();
  await page
    .getByLabel("API 地址", { exact: true })
    .fill("https://example.com/v1");
  await page.getByLabel("API Key", { exact: true }).fill("synthetic-secret");
  await page.getByLabel("模型名称", { exact: true }).fill("test-model");
  await page.getByRole("button", { name: "保存配置", exact: true }).click();
  await expect(page.getByLabel("API Key", { exact: true })).toHaveValue("");
  await expect(page.getByText("已保存密钥 · 留空即可继续使用")).toBeVisible();
  expect(await page.evaluate(() => JSON.stringify(localStorage))).not.toContain(
    "synthetic-secret",
  );
  await page.getByRole("button", { name: "关闭设置" }).click();
  await page.reload();
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await expect(page.getByLabel("模型名称", { exact: true })).toHaveValue(
    "test-model",
  );
  await page.route("**/api/test-speedread-config", async (route) => {
    expect(route.request().postDataJSON()).toEqual({
      apiConfig: { useSaved: true },
    });
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        preview: "Synthetic connection verified",
      }),
    });
  });
  await page.getByRole("button", { name: "测试接口（会调用模型）" }).click();
  await expect(page.getByText("Synthetic connection verified")).toBeVisible();
  await page.getByLabel("模型名称", { exact: true }).fill("draft-model");
  await page.route("**/api/settings", async (route) => {
    if (route.request().method() === "POST")
      await route.fulfill({
        status: 409,
        contentType: "application/json",
        body: JSON.stringify({ ok: false, error: "配置已被修改，请重新加载" }),
      });
    else await route.continue();
  });
  await page.getByRole("button", { name: "保存配置", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("配置已被修改");
  await expect(page.getByLabel("模型名称", { exact: true })).toHaveValue(
    "draft-model",
  );
  await page.screenshot({
    path: "test-results/vue-settings.png",
    fullPage: true,
  });
  await page.unroute("**/api/settings");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "重新加载", exact: true }).click();
  await expect(page.getByLabel("模型名称", { exact: true })).toHaveValue(
    "test-model",
  );
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "清空配置", exact: true }).click();
  await expect(page.getByText("尚未保存密钥")).toBeVisible();
});

test("legacy import removes browser key only after verified backend save", async ({
  page,
}) => {
  await page.goto("/app/");
  await page.evaluate(() =>
    localStorage.setItem(
      "papers-visualizer-speedread-config-v1",
      JSON.stringify({
        apiBaseUrl: "https://example.com/v1",
        apiKey: "legacy-synthetic-secret",
        model: "legacy-model",
        timeoutSec: 180,
        contextWindow: 0,
        maxOutputTokens: 0,
      }),
    ),
  );
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await expect(page.getByRole("button", { name: "导入旧配置" })).toBeEnabled();
  await page.route("**/api/settings", async (route) => {
    if (route.request().method() === "POST")
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          ok: false,
          error: "Synthetic vault unavailable",
        }),
      });
    else await route.continue();
  });
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "导入旧配置" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Synthetic vault unavailable",
  );
  expect(
    await page.evaluate(
      () =>
        localStorage.getItem("papers-visualizer-speedread-config-v1") !== null,
    ),
  ).toBe(true);
  await page.unroute("**/api/settings");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "导入旧配置" }).click();
  await expect(page.getByLabel("模型名称", { exact: true })).toHaveValue(
    "legacy-model",
  );
  expect(
    await page.evaluate(() =>
      localStorage.getItem("papers-visualizer-speedread-config-v1"),
    ),
  ).toBeNull();
  await expect(page.getByLabel("API Key", { exact: true })).toHaveValue("");
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "清空配置", exact: true }).click();
  await expect(page.getByText("尚未保存密钥")).toBeVisible();
});

test("imports a real PDF, deduplicates retry and rejects corrupt files", async ({
  page,
}) => {
  const demo = resolve("../papers/demo");
  const pdf = readFileSync(
    resolve(
      demo,
      readdirSync(demo).find((name) => name.endsWith(".pdf"))!,
    ),
  );
  await page.goto("/app/");
  await expect(page.locator(".paper-card")).toHaveCount(3);
  const upload = {
    name: "Imported example.pdf",
    mimeType: "application/pdf",
    buffer: pdf,
  };
  await page.getByLabel("选择 PDF 文件").setInputFiles(upload);
  await expect(page.getByRole("region", { name: "导入结果" })).toContainText(
    "已导入",
  );
  await expect(page.locator(".paper-card")).toHaveCount(4);
  await page.getByRole("button", { name: /编辑：Imported example/ }).click();
  const pdfHref = await page
    .getByRole("link", { name: "打开原始 PDF" })
    .getAttribute("href");
  expect((await page.request.get(pdfHref!)).status()).toBe(200);
  await page.getByRole("button", { name: "取消", exact: true }).click();

  await page.getByLabel("选择 PDF 文件").setInputFiles(upload);
  await expect(page.getByRole("region", { name: "导入结果" })).toContainText(
    "未重复导入",
  );
  await expect(page.locator(".paper-card")).toHaveCount(4);
  await page.getByLabel("选择 PDF 文件").setInputFiles({
    name: "broken.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("not a PDF"),
  });
  await expect(page.getByRole("region", { name: "导入结果" })).toContainText(
    "不是可读取的 PDF",
  );
  await expect(page.locator(".paper-card")).toHaveCount(4);
  // Clean up only the synthetic imported file in this disposable test library.
  const headers = { "X-OpenPaper-Request": "1" };
  await page.request.post("/api/delete-paper", {
    headers,
    data: { file_key: "imported/imported example.pdf" },
  });
  const bin = await (await page.request.get("/api/recycle-list")).json();
  for (const item of bin.items.filter(
    (item: { file_key: string }) =>
      item.file_key === "imported/imported example.pdf",
  ))
    await page.request.post("/api/recycle-purge", {
      headers,
      data: { id: item.id },
    });
});
