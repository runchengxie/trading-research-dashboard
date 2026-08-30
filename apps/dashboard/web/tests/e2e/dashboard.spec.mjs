import { expect, test } from '@playwright/test';

function installDiagnostics(page) {
  page.on('console', (message) => {
    if (message.type() === 'error' || message.type() === 'warning') {
      console.log(`[browser console ${message.type()}] ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => {
    console.log(`[browser pageerror] ${error.stack ?? error.message}`);
  });
  page.on('requestfailed', (request) => {
    console.log(
      `[browser requestfailed] ${request.method()} ${request.url()} ${request.failure()?.errorText ?? ''}`,
    );
  });
}

async function gotoDashboard(page) {
  installDiagnostics(page);
  const response = await page.goto('/');
  console.log(`[browser navigation] ${response?.status() ?? 'no response'} ${page.url()}`);
  await page.waitForLoadState('networkidle');
  if ((await page.getByRole('heading', { name: 'Trading Dashboard' }).count()) === 0) {
    console.log(`[browser body] ${await page.locator('body').innerText()}`);
    console.log(`[browser root] ${await page.locator('#root').innerHTML()}`);
  }
}

async function expectMarketAreaUsable(page) {
  const workspaceTab = page.locator('.section-nav-button').filter({ hasText: '日内工作台' });
  await expect(workspaceTab).toBeVisible();
  await workspaceTab.click();
  await expect(page.getByRole('heading', { name: /日内工作台/ })).toBeVisible();
  await expect(page.locator('.selected-instrument-workspace')).toBeVisible();
  await expect(page.locator('.selected-instrument-workspace canvas').first()).toBeVisible();
}

test('首页加载并提供三段式导航', async ({ page }) => {
  await gotoDashboard(page);

  await expect(page.getByRole('heading', { name: 'Trading Dashboard' })).toBeVisible();
  await expect(page.getByRole('button', { name: '盘前概览' })).toBeVisible();
  await expect(page.locator('.section-nav-button').filter({ hasText: '日内工作台' })).toBeVisible();
  await expect(page.getByRole('button', { name: '策略研究' })).toBeVisible();
  await expect(page.getByRole('heading', { name: '标的概览' })).toBeVisible();
  await expect(page.locator('.instrument-overview-card').first()).toBeVisible();

  await expectMarketAreaUsable(page);
  await page.getByRole('button', { name: '策略研究' }).click();
  await expect(page.getByRole('heading', { name: '牛门线全市场样本外研究' })).toBeVisible();
  await expect(page.locator('.research-section canvas').first()).toBeVisible();
});

test('选择标的后日内工作台只展示当前标的', async ({ page }) => {
  await gotoDashboard(page);

  const cards = page.locator('.instrument-overview-card');
  const selectedCode = await cards.first().getAttribute('data-code');
  await cards.first().click();
  await page.getByRole('button', { name: '日内工作台', exact: true }).click();

  await expect(page.getByRole('heading', { name: /日内工作台/ })).toContainText(selectedCode ?? '');
  await expect(page.locator('.selected-instrument-workspace')).toHaveCount(1);
  await expect(page.locator('.selected-instrument-workspace .indicator-table')).toHaveCount(1);
  await expect(page.getByLabel('显示全部价位')).not.toBeChecked();
  await page.getByLabel('显示全部价位').check();
  await expect(page.getByLabel('显示全部价位')).toBeChecked();
  await expect(page.getByText('距当前价', { exact: false }).first()).toBeVisible();
  await expect(page.getByText('展开高级指标')).toBeVisible();
});

test('市场筛选在没有美股快照时提供明确入口提示', async ({ page }) => {
  await page.route('**/data.json', async (route) => {
    const response = await route.fetch();
    const payload = await response.json();
    payload.stocks = payload.stocks.filter((stock) => stock.market !== 'US');
    await route.fulfill({
      response,
      contentType: 'application/json',
      body: JSON.stringify(payload),
    });
  });
  await gotoDashboard(page);

  const usFilter = page.getByRole('button', { name: /美股/ });
  await expect(usFilter).toBeVisible();
  await usFilter.click();

  await expect(page.locator('.empty-market-state')).toContainText('当前快照没有美股标的');
  await expect(page.locator('.empty-market-state')).toContainText('AAPL.US');
});

test('research.json 缺失时行情区域继续可用', async ({ page }) => {
  await page.route('**/research.json', async (route) => {
    await route.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
  });

  await gotoDashboard(page);

  await expectMarketAreaUsable(page);
  await page.getByRole('button', { name: '策略研究' }).click();
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

  await gotoDashboard(page);

  await expectMarketAreaUsable(page);
  await page.getByRole('button', { name: '策略研究' }).click();
  await expect(page.getByText(/research.json 加载失败：不支持的研究快照版本/)).toBeVisible();
});

test('策略研究提供牛门线、R-Breaker 和对比入口', async ({ page }) => {
  await gotoDashboard(page);
  await page.getByRole('button', { name: '策略研究' }).click();

  await expect(page.getByRole('button', { name: /牛门线/ })).toBeVisible();
  await expect(page.getByRole('button', { name: /R-Breaker/ })).toContainText('已发布');
  await page.getByRole('button', { name: /R-Breaker/ }).click();
  await expect(page.getByRole('heading', { name: 'R-Breaker全市场样本外研究' })).toBeVisible();

  await page.getByRole('button', { name: '策略对比' }).click();
  await expect(page.getByRole('heading', { name: '共同变体指标' })).toBeVisible();
});

test('深色主题切换后页面与图表继续渲染', async ({ page }) => {
  await page.addInitScript(() => window.localStorage.setItem('theme', 'light'));
  await gotoDashboard(page);
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');

  await page.getByRole('button', { name: '切换主题' }).click();

  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expectMarketAreaUsable(page);
  await page.getByRole('button', { name: '策略研究' }).click();
  await expect(page.locator('.research-section canvas').first()).toBeVisible();
});

test('390 像素宽度下页面不横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await gotoDashboard(page);
  await expectMarketAreaUsable(page);
  await page.getByRole('button', { name: '策略研究' }).click();

  const documentOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(documentOverflow).toBeLessThanOrEqual(1);

  const tableOverflow = await page.locator('.research-table-wrap').evaluate(
    (element) => element.scrollWidth > element.clientWidth,
  );
  expect(tableOverflow).toBe(true);
});
