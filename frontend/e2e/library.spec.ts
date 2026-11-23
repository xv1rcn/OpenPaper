import { test, expect } from "./fixtures";
test("library edits persist, deletion restores and filters remain usable", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/app/");
  await expect(page.locator(".paper-card")).toHaveCount(3);
  await page
    .getByRole("textbox", { name: "搜索论文" })
    .fill("out-of-distribution");
  await expect(page.locator(".paper-card")).toHaveCount(1);
  await page.getByRole("button", { name: /标记已读：Understanding/ }).click();
  await expect(page.locator(".read-badge")).toHaveCount(1);
  await page.getByRole("button", { name: /编辑：Understanding/ }).click();
  await page.getByLabel("标签", { exact: true }).fill("OOD, Robustness");
  await page.getByLabel("阅读笔记").fill("Follow up on evaluation protocol.");
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Robustness", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Robustness", exact: true }).click();
  await expect(page.locator(".paper-card")).toHaveCount(1);
  await page.getByRole("button", { name: /编辑：Understanding/ }).click();
  await expect(page.getByLabel("阅读笔记")).toHaveValue(
    "Follow up on evaluation protocol.",
  );
  await page.getByRole("button", { name: "移入回收站" }).click();
  await page.getByRole("alertdialog").getByRole("button").last().click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: /回收站/ }).click();
  await expect(page.locator(".recycle-row")).toHaveCount(1);
  await page.getByRole("button", { name: "恢复", exact: true }).click();
  await expect(page.locator(".recycle-row")).toHaveCount(0);
  await page.getByRole("button", { name: /全部论文/ }).click();
  await expect(page.locator(".paper-card")).toHaveCount(3);
  await page.getByRole("button", { name: "列表视图" }).click();
  await expect(page.locator(".paper-row")).toHaveCount(3);
  await page.reload();
  await expect(page.locator(".paper-row")).toHaveCount(3);
  expect(errors).toEqual([]);
});
test("empty search, mobile layout and keyboard access", async ({ page }) => {
  await page.goto("/app/");
  await expect(page.locator(".paper-card")).toHaveCount(3);
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("textbox", { name: "搜索论文" })).toBeFocused();
  await page.keyboard.type("no-such-paper");
  await expect(page.getByText("没有匹配的论文")).toBeVisible();
  await page.getByRole("button", { name: "查看全部论文" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".paper-card")).toHaveCount(3);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/library-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "test-results/library-desktop.png",
    fullPage: true,
  });
});

test("failed save keeps the editor draft and can be retried", async ({
  page,
}) => {
  await page.goto("/app/");
  await page.getByRole("button", { name: /编辑：Exploring/ }).click();
  await page.getByLabel("阅读笔记").fill("Draft survives a failed save");
  await page.route("**/api/update-paper", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ ok: false, error: "Test write failure" }),
    }),
  );
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByLabel("阅读笔记")).toHaveValue(
    "Draft survives a failed save",
  );
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText(
    "Test write failure",
  );
  await page.unroute("**/api/update-paper");
  await page.getByRole("button", { name: "保存修改" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /编辑：Exploring/ }),
  ).toBeFocused();
});
