import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";

test("legacy entry points open the Vue library, statistics and cached reader", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/app\/$/);
  await page.goto("/stats.html");
  await expect(page.locator(".statistics-panel")).toBeVisible();
  await page.route("**/api/speedread-cache?*", (route) =>
    route.fulfill({
      json: {
        ok: true,
        speed_read: {
          status: "success",
          content: {
            one_sentence: "Cached research summary",
            quick_takeaways: ["Test takeaway"],
          },
        },
      },
    }),
  );
  await page.goto("/quick-reading.html?file_key=fixture-0.pdf");
  await expect(page).toHaveURL(/\/app\/\?file_key=fixture-0.pdf/);
  await expect(page.getByText("Cached research summary")).toBeVisible();
  await expect(page.getByText("Test takeaway")).toBeVisible();
  await expect(page.getByTitle("PDF 原文")).toHaveAttribute(
    "src",
    /fixture-0.pdf#page=1/,
  );
  await page.getByLabel("PDF 页码").fill("2");
  await page.getByLabel("PDF 页码").press("Tab");
  await page.reload();
  await expect(page.getByLabel("PDF 页码")).toHaveValue("2");
});

test("appearance survives reload and tab changes preserve drafts", async ({
  page,
}) => {
  await page.goto("/app/");
  await page.getByRole("button", { name: "设置" }).click();
  await page.getByRole("button", { name: "外观", exact: true }).click();
  await page.getByRole("button", { name: "深色", exact: true }).click();
  await page.getByRole("button", { name: "速读", exact: true }).click();
  await page.getByRole("button", { name: "外观", exact: true }).click();
  await expect(page.getByLabel("页面背景")).toHaveValue("#1d2520");
  await page.getByRole("button", { name: "保存外观" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "设置" }).click();
  await page.getByRole("button", { name: "外观", exact: true }).click();
  await expect(page.getByLabel("页面背景")).toHaveValue("#1d2520");
  await page.getByRole("button", { name: "恢复默认" }).click();
  await page.getByRole("button", { name: "保存外观" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("group order persists and metadata export retains original fields", async ({
  page,
}) => {
  await page.goto("/app/");
  await page.getByRole("button", { name: "按标签分组" }).click();
  const first = await page.locator(".paper-group header").first().innerText();
  await page
    .getByRole("button", { name: /下移分组/ })
    .first()
    .click();
  await page.reload();
  await expect(page.locator(".paper-group header").first()).not.toHaveText(
    first!,
  );
  await page.getByRole("button", { name: "折叠全部分组" }).click();
  await expect(page.locator(".paper-card")).toHaveCount(0);
  await page.getByRole("button", { name: "展开全部分组" }).click();
  await expect(page.locator(".paper-card").first()).toBeVisible();
  await page.getByRole("button", { name: "导出与管理" }).click();
  const downloading = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出元数据 JSON" }).click();
  const download = await downloading;
  const data = JSON.parse(await readFile((await download.path())!, "utf8"));
  expect(data["fixture-0.pdf"].authors).toBe("Test Author");
  expect(data["fixture-0.pdf"].file_key).toBe("fixture-0.pdf");
});

test("settings are unified and statistics include legacy analysis controls", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/app/");
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await expect(
    page
      .getByRole("dialog")
      .getByRole("heading", { name: "设置", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "外观", exact: true }).click();
  await expect(page.getByRole("button", { name: "载入旧版外观" })).toHaveCount(
    0,
  );
  await expect(
    page.getByText("外观独立保存在本机，不影响模型或密钥配置。"),
  ).toHaveCount(0);
  await page.screenshot({ path: "test-results/settings-clean.png" });
  await page.getByRole("button", { name: "关闭设置" }).click();
  await page.keyboard.press("/");
  await expect(page.getByRole("textbox", { name: "搜索论文" })).toBeFocused();
  await page.getByRole("button", { name: "统计面板", exact: true }).click();
  for (const name of [
    "累计增长与阅读进度",
    "周新增量",
    "各标签阅读进度",
    "加入热力图",
    "标签 × 年份",
    "论文关系",
    "近期新增",
  ]) {
    await expect(
      page.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
  }
  await page.getByLabel("分组依据").selectOption("year");
  await page
    .getByRole("button", { name: "查看分类 2024", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "2024 · 1 篇" }),
  ).toBeVisible();
  await page.getByLabel("隐藏论文节点").check();
  await expect(page.locator(".relationship-graph a")).toHaveCount(0);
  await page.getByLabel("隐藏论文节点").uncheck();
  await expect(page.locator(".relationship-graph a")).toHaveCount(
    (await (await page.request.get("/api/library")).json()).papers.length,
  );
  await page.getByLabel("缩放").fill("2");
  await page.getByRole("button", { name: "重置视图" }).click();
  await expect(page.getByLabel("缩放")).toHaveValue("1");
  await page.screenshot({
    path: "test-results/statistics-complete.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

test("card notes and speedread states remain visible in the new library", async ({
  page,
}) => {
  await page.route("**/api/library", async (route) => {
    const response = await route.fetch();
    const data = await response.json();
    data.papers[0].speedread_status = "running";
    data.papers[0].notes =
      "Visible note from the original library https://example.com/paper javascript:alert(1) <script>alert(1)</script>";
    await route.fulfill({ response, json: data });
  });
  await page.goto("/app/");
  await expect(page.getByRole("link", { name: "速读生成中…" })).toBeVisible();
  const card = page
    .locator(".paper-card")
    .filter({ has: page.getByRole("link", { name: "速读生成中…" }) });
  await card.getByText("阅读笔记", { exact: true }).click();
  await expect(
    card.getByText("Visible note from the original library", { exact: false }),
  ).toBeVisible();
});

// Link creation is limited to HTTP(S); note text never becomes HTML.
