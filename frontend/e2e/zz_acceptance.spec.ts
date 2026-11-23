import { test, expect } from "./fixtures";
import { execFileSync } from "node:child_process";
const python = process.env.OPENPAPER_TEST_PYTHON || "../.venv/bin/python";

test("unsaved paper drafts survive dismissed close and reload prompts", async ({
  page,
}) => {
  await page.goto("/app/");
  await page.getByRole("button", { name: /编辑：Exploring/ }).click();
  const notes = page.getByLabel("阅读笔记");
  await notes.fill("Unsaved acceptance draft");
  page.once("dialog", (d) => d.dismiss());
  await page.getByRole("button", { name: "取消", exact: true }).click();
  await expect(notes).toHaveValue("Unsaved acceptance draft");
  page.once("dialog", (d) => d.dismiss());
  await page.keyboard.press("Escape");
  await expect(notes).toHaveValue("Unsaved acceptance draft");
  const prompt = page.waitForEvent("dialog");
  const reloading = page.reload({ timeout: 2000 }).catch(() => null);
  const dialog = await prompt;
  expect(dialog.type()).toBe("beforeunload");
  await dialog.dismiss();
  await reloading;
  await expect(notes).toHaveValue("Unsaved acceptance draft");
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "取消", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("cached reading exports real PDF/PPTX content and restores deleted cache", async ({
  page,
}) => {
  test.setTimeout(90000);
  await page.goto("/app/?file_key=fixture-2.pdf");
  await expect(
    page.getByText("Verified cached summary", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "第 2 页", exact: true }).click();
  await expect(page.getByLabel("PDF 页码")).toHaveValue("2");
  await page.getByRole("button", { name: "重新生成速读" }).click();
  await expect(page.getByRole("combobox", { name: "深度" })).toHaveValue(
    "deep",
  );
  await expect(page.getByLabel("补充要求")).toHaveValue("Keep evidence");
  await expect(page.getByLabel("包含图表解读")).not.toBeChecked();
  for (const format of ["PDF", "PPTX"]) {
    const downloading = page.waitForEvent("download");
    await page.getByRole("button", { name: format, exact: true }).click();
    const download = await downloading;
    expect(download.suggestedFilename()).toContain("Exploring");
    const path = (await download.path())!;
    const script =
      format === "PDF"
        ? 'import fitz,sys; d=fitz.open(sys.argv[1]); assert d.page_count>0; print("\\n".join(p.get_text() for p in d))'
        : 'from pptx import Presentation; import sys; p=Presentation(sys.argv[1]); assert len(p.slides)>1; print("\\n".join(s.text for slide in p.slides for s in slide.shapes if s.has_text_frame))';
    const text = execFileSync(python, ["-c", script, path], {
      encoding: "utf8",
    });
    expect(text).toContain("Verified cached summary");
    expect(text).toContain("Evidence survives export");
    expect(text).toContain("Module A");
    expect(text.replace(/\s+/g, "")).toContain("LONG-CONTENT-END");
  }
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "删除速读" }).click();
  await expect(page.getByText("原文已就绪")).toBeVisible();
  await page.getByRole("link", { name: "书库", exact: true }).click();
  await page.getByRole("button", { name: /回收站/ }).click();
  const row = page.locator(".recycle-row").filter({ hasText: "Exploring" });
  await row.getByRole("button", { name: "恢复", exact: true }).click();
  await expect(row).toHaveCount(0);
  await page.goto("/app/?file_key=fixture-2.pdf");
  await expect(
    page.getByText("Verified cached summary", { exact: true }),
  ).toBeVisible();
});

test("generation errors remain actionable and retries use saved credentials only", async ({
  page,
}) => {
  await page.route("**/api/speedread-cache?*", (r) =>
    r.fulfill({
      json: {
        ok: true,
        speed_read: { status: "error", error: "Synthetic model failure" },
      },
    }),
  );
  let attempts = 0;
  await page.route("**/api/generate-speedread", async (route) => {
    const body = route.request().postDataJSON();
    expect(body.apiConfig).toEqual({ useSaved: true });
    expect(body.file_key).toBe("fixture-2.pdf");
    attempts++;
    await route.fulfill({
      status: 503,
      json: { ok: false, error: "Synthetic service unavailable" },
    });
  });
  await page.goto("/app/?file_key=fixture-2.pdf");
  await expect(page.getByText("Synthetic model failure")).toBeVisible();
  for (let i = 0; i < 2; i++) {
    await page.getByRole("button", { name: "生成速读", exact: true }).click();
    await page.getByRole("button", { name: "开始生成（会调用模型）" }).click();
    await expect(page.getByText(/Synthetic service unavailable/)).toBeVisible();
  }
  expect(attempts).toBe(2);
});

test("appearance conflict keeps drafts and discarding leaves the saved theme intact", async ({
  page,
}) => {
  await page.goto("/app/");
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await page.getByRole("button", { name: "外观", exact: true }).click();
  await page.getByRole("button", { name: "深色", exact: true }).click();
  await page.route("**/api/preferences", (route) =>
    route.request().method() === "POST"
      ? route.fulfill({
          status: 409,
          json: { ok: false, error: "外观已在其他页面修改" },
        })
      : route.continue(),
  );
  await page.getByRole("button", { name: "保存外观" }).click();
  await expect(page.getByRole("alert")).toContainText("外观已在其他页面修改");
  await expect(page.getByLabel("页面背景")).toHaveValue("#1d2520");
  page.once("dialog", (d) => d.dismiss());
  await page.getByRole("button", { name: "关闭设置" }).click();
  await expect(page.getByLabel("页面背景")).toHaveValue("#1d2520");
  page.once("dialog", (d) => d.accept());
  await page.getByRole("button", { name: "关闭设置" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});
