import { expect, test } from '@playwright/test';

async function expectMarketAreaUsable(page) {
  await expect(page.getByRole('heading', { name: '价格、VWAP、ORB 与分时图' })).toBeVisible();
  await expect(page.locator('.stock-card').first()).toBeVisible();
  await expect(page.locator('.stock-card canvas').first()).toBeVisible();
}

test('首页加载并渲染 ECharts 与研究区域', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'A股交易研究仪表盘' })).toBeVisible();
  await expectMarketAreaUsable(page);
  await expect(page.getByRole('heading', { name: '牛门线全市场样本外研究' })).toBeVisible();
  await expect(page.locator('.research-section canvas').first()).toBeVisible();
});

test('research.json 缺失时行情区域继续可用', async ({ page }) => {
  await page.route('**/research.json', async (route) => {
    await route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
  });

  await page.goto('/');

  await expectMarketAreaUsable(page);
  await expect(page.getByText('当前部署尚未包含')).toBeVisible();
});

test('研究快照 schema 不受支持时只在研究区域报错', async ({ page }) => {
  await page.route('**/research.json', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ schemaVersion: 'niu_men.research_snapshot.v999' }),
    });
  });

  await page.goto('/');

  await expectMarketAreaUsable(page);
  await expect(page.getByText(/research.json 加载失败：不支持的研究快照版本/)).toBeVisible();
});

test('深色主题切换后页面与图表继续渲染', async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem('theme', 'light'));
  await page.goto('/');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');

  await page.getByRole('button', { name: '切换主题' }).click();

  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expectMarketAreaUsable(page);
  await expect(page.locator('.research-section canvas').first()).toBeVisible();
});

test('390 像素宽度下页面不横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expectMarketAreaUsable(page);

  const documentOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(documentOverflow).toBeLessThanOrEqual(1);

  const tableOverflow = await page.locator('.research-table-wrap').evaluate(
    (element) => element.scrollWidth > element.clientWidth,
  );
  expect(tableOverflow).toBe(true);
});
