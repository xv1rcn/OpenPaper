import { test, expect } from "./fixtures";

test("native close request preserves drafts on cancel and emits approval only after confirmation", async ({
  page,
}) => {
  const actions: string[] = [];
  await page.addInitScript(() => {
    (
      window as Window & { __OPENPAPER_DESKTOP__?: boolean }
    ).__OPENPAPER_DESKTOP__ = true;
  });
  // Model the host's cancelled navigation signals, without exiting the browser.
  await page.route("**/desktop/*", async (route) => {
    actions.push(new URL(route.request().url()).pathname);
    await route.abort();
  });
  await page.goto("/app/");
  await expect.poll(() => actions.includes("/desktop/ui-ready")).toBe(true);
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await page
    .getByLabel("模型名称", { exact: true })
    .fill("unsaved-desktop-draft");
  await page.evaluate(() =>
    window.dispatchEvent(new Event("openpaper-close-request")),
  );
  const dialog = page.getByRole("alertdialog");
  await expect(dialog).toContainText("放弃修改并退出");
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  await expect(page.getByLabel("模型名称", { exact: true })).toHaveValue(
    "unsaved-desktop-draft",
  );
  expect(actions).not.toContain("/desktop/close-approved");
  await page.evaluate(() =>
    window.dispatchEvent(new Event("openpaper-close-request")),
  );
  await dialog
    .getByRole("button", { name: "放弃修改并退出", exact: true })
    .click();
  await expect
    .poll(() => actions.includes("/desktop/close-approved"))
    .toBe(true);
});

test("backend failure keeps the editing page and guards restart", async ({
  page,
}) => {
  const actions: string[] = [];
  await page.addInitScript(() => {
    (
      window as Window & { __OPENPAPER_DESKTOP__?: boolean }
    ).__OPENPAPER_DESKTOP__ = true;
  });
  await page.route("**/desktop/*", async (route) => {
    actions.push(new URL(route.request().url()).pathname);
    await route.abort();
  });
  await page.goto("/app/");
  await expect.poll(() => actions.includes("/desktop/ui-ready")).toBe(true);
  await page.getByRole("button", { name: "设置", exact: true }).click();
  await page.getByLabel("模型名称", { exact: true }).fill("keep-after-crash");
  await page.evaluate(() =>
    window.dispatchEvent(new Event("openpaper-backend-stopped")),
  );
  await expect(page.locator(".desktop-recovery")).toContainText(
    "本地服务已停止",
  );
  await expect(page.getByLabel("模型名称", { exact: true })).toHaveValue(
    "keep-after-crash",
  );
  await page.locator(".desktop-recovery button").click();
  const dialog = page.getByRole("alertdialog");
  await expect(dialog).toContainText("放弃修改并重启");
  await dialog.getByRole("button", { name: "取消", exact: true }).click();
  expect(actions).not.toContain("/desktop/restart-approved");
  await expect(page.getByLabel("模型名称", { exact: true })).toHaveValue(
    "keep-after-crash",
  );
});
