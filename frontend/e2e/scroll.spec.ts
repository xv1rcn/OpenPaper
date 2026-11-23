import { test, expect } from "./fixtures";
for (const size of [
  { width: 1024, height: 768 },
  { width: 900, height: 600 },
]) {
  test(`library scroll leaves chrome fixed at ${size.width}x${size.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(size);
    await page.route("**/api/library", async (route) => {
      const response = await route.fetch();
      const data = await response.json();
      data.papers = Array.from({ length: 40 }, (_, i) => ({
        ...data.papers[0],
        file_key: `test-${i}.pdf`,
        tags: [`Tag ${i}`],
      }));
      await route.fulfill({ response, json: data });
    });
    await page.goto("/app/");
    await expect(page.locator(".paper-card")).toHaveCount(40);
    const before = await page.locator(".topbar").boundingBox();
    const settings = await page
      .getByRole("button", { name: "设置", exact: true })
      .boundingBox();
    expect(settings!.y + settings!.height).toBeLessThanOrEqual(size.height);
    await page.locator(".library-content").hover();
    await page.mouse.wheel(0, 1000);
    await expect
      .poll(() =>
        page.locator(".library-content").evaluate((el) => el.scrollTop),
      )
      .toBeGreaterThan(100);
    expect(await page.locator(".topbar").boundingBox()).toEqual(before);
    expect(
      await page
        .getByRole("button", { name: "设置", exact: true })
        .boundingBox(),
    ).toEqual(settings);
    expect(
      await page.evaluate(() => document.scrollingElement!.scrollTop),
    ).toBe(0);
    const tags = page.locator(".tag-navigation");
    await tags.hover();
    await page.mouse.wheel(0, 1000);
    await expect
      .poll(() => tags.evaluate((el) => el.scrollTop))
      .toBeGreaterThan(0);
    expect(
      await page
        .getByRole("button", { name: "设置", exact: true })
        .boundingBox(),
    ).toEqual(settings);
  });
  test(`reader scroll stays in panes at ${size.width}x${size.height}`, async ({
    page,
  }) => {
    await page.setViewportSize(size);
    await page.goto("/app/?file_key=fixture-2.pdf");
    await expect(page.locator(".pdfViewer canvas").first()).toBeVisible();
    const toolbar = await page.locator(".reader-toolbar").boundingBox();
    await page.locator(".reading-content").hover();
    await page.mouse.wheel(0, 1000);
    await expect
      .poll(() =>
        page.locator(".reading-content").evaluate((el) => el.scrollTop),
      )
      .toBeGreaterThan(100);
    expect(await page.locator(".reader-toolbar").boundingBox()).toEqual(
      toolbar,
    );
    await page.locator(".pdf-scroll").hover();
    await page.mouse.wheel(0, 1000);
    await expect
      .poll(() => page.locator(".pdf-scroll").evaluate((el) => el.scrollTop))
      .toBeGreaterThan(100);
    expect(await page.locator(".reader-toolbar").boundingBox()).toEqual(
      toolbar,
    );
    expect(
      await page.evaluate(
        () => document.scrollingElement!.scrollHeight <= innerHeight + 1,
      ),
    ).toBe(true);
    await page.getByRole("button", { name: "重新生成速读" }).click();
    await expect(
      page.getByRole("heading", { name: "生成速读" }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.scrollingElement!.scrollHeight <= innerHeight + 1,
      ),
    ).toBe(true);
  });
}
