import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

test('legacy entry points open the Vue library, statistics and cached reader', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/app\/$/);
  await page.goto('/stats.html');
  await expect(page.locator('.statistics-panel')).toBeVisible();
  await page.route('**/api/speedread-cache?*', route => route.fulfill({ json: {
    ok: true, speed_read: { status: 'success', content: { one_sentence: 'Cached research summary', quick_takeaways: ['Test takeaway'] } }
  }}));
  await page.goto('/quick-reading.html?file_key=fixture-0.pdf');
  await expect(page).toHaveURL(/\/app\/\?file_key=fixture-0.pdf/);
  await expect(page.getByText('Cached research summary')).toBeVisible();
  await expect(page.getByText('Test takeaway')).toBeVisible();
  await expect(page.getByTitle('PDF 原文')).toHaveAttribute('src', /fixture-0.pdf#page=1/);
  await page.getByLabel('PDF 页码').fill('2');
  await page.getByLabel('PDF 页码').press('Tab');
  await page.reload();
  await expect(page.getByLabel('PDF 页码')).toHaveValue('2');
});

test('appearance survives reload and tab changes preserve drafts', async ({ page }) => {
  await page.goto('/app/');
  await page.getByRole('button', { name: '速读设置' }).click();
  await page.getByRole('button', { name: '外观', exact: true }).click();
  await page.getByRole('button', { name: '深色', exact: true }).click();
  await page.getByRole('button', { name: '模型服务', exact: true }).click();
  await page.getByRole('button', { name: '外观', exact: true }).click();
  await expect(page.getByLabel('页面背景')).toHaveValue('#1d2520');
  await page.getByRole('button', { name: '保存外观' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.getByRole('button', { name: '速读设置' }).click();
  await page.getByRole('button', { name: '外观', exact: true }).click();
  await expect(page.getByLabel('页面背景')).toHaveValue('#1d2520');
  await page.getByRole('button', { name: '恢复默认' }).click();
  await page.getByRole('button', { name: '保存外观' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
});

test('group order persists and metadata export retains original fields', async ({ page }) => {
  await page.goto('/app/');
  await page.getByRole('button', { name: '按标签分组' }).click();
  const first = await page.locator('.paper-group header').first().innerText();
  await page.getByRole('button', { name: /下移分组/ }).first().click();
  await page.reload();
  await expect(page.locator('.paper-group header').first()).not.toHaveText(first!);
  await page.getByRole('button', { name: '折叠全部分组' }).click();
  await expect(page.locator('.paper-card')).toHaveCount(0);
  await page.getByRole('button', { name: '展开全部分组' }).click();
  await expect(page.locator('.paper-card').first()).toBeVisible();
  await page.getByRole('button', { name: '导出与管理' }).click();
  const downloading = page.waitForEvent('download');
  await page.getByRole('button', { name: '导出元数据 JSON' }).click();
  const download = await downloading;
  const data = JSON.parse(await readFile((await download.path())!, 'utf8'));
  expect(data['fixture-0.pdf'].authors).toBe('Test Author');
  expect(data['fixture-0.pdf'].file_key).toBe('fixture-0.pdf');
});
