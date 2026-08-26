import { access, mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { chromium } from '@playwright/test';
import { preview } from 'vite';

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const WEB_ROOT = path.resolve(SCRIPT_DIR, '..');
const REPO_ROOT = path.resolve(WEB_ROOT, '../../..');
const DEFAULT_OUTPUT_ROOT = path.join(REPO_ROOT, 'artifacts', 'charts');

export function parseArgs(argv, env = process.env) {
  const options = {
    url: env.DASHBOARD_EXPORT_URL?.trim() || null,
    output: env.DASHBOARD_EXPORT_DIR?.trim() || null,
    theme: env.DASHBOARD_EXPORT_THEME?.trim() || 'light',
  };

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === '--url' || argument === '--output' || argument === '--theme') {
      const value = argv[index + 1];
      if (!value) {
        throw new Error(`${argument} 缺少参数值`);
      }
      options[argument.slice(2)] = value;
      index += 1;
      continue;
    }
    if (argument === '--help' || argument === '-h') {
      options.help = true;
      continue;
    }
    throw new Error(`不支持的参数：${argument}`);
  }

  if (!['light', 'dark'].includes(options.theme)) {
    throw new Error(`theme 只支持 light 或 dark，当前值：${options.theme}`);
  }
  return options;
}

export function safeFileStem(value) {
  const stem = String(value)
    .trim()
    .replace(/[^A-Za-z0-9._-]+/g, '_')
    .replace(/^_+|_+$/g, '');
  return stem || 'chart';
}

export function buildExportManifest({
  generatedAt,
  exportedAt,
  sourceUrl,
  theme,
  images,
}) {
  return {
    schemaVersion: 'trading_research.chart_export.v1',
    generatedAt,
    exportedAt,
    sourceUrl,
    theme,
    images,
  };
}

function usage() {
  return `导出 Dashboard 图表图片\n\n` +
    `用法：\n` +
    `  npm run export:charts\n` +
    `  npm run export:charts -- --url https://example.com/ --output /path/to/charts\n\n` +
    `参数：\n` +
    `  --url     已部署 Dashboard 地址。省略时自动预览本地 dist\n` +
    `  --output  输出根目录，默认 ${DEFAULT_OUTPUT_ROOT}\n` +
    `  --theme   light 或 dark，默认 light\n`;
}

function normalizeBaseUrl(value) {
  const url = new URL(value);
  if (!url.pathname.endsWith('/')) {
    url.pathname += '/';
  }
  return url.toString();
}

async function loadDashboard(baseUrl) {
  const response = await fetch(new URL('data.json', baseUrl));
  if (!response.ok) {
    throw new Error(`读取 data.json 失败：HTTP ${response.status}`);
  }
  const payload = await response.json();
  if (
    !payload ||
    typeof payload.generatedAt !== 'string' ||
    !Array.isArray(payload.stocks) ||
    payload.stocks.length === 0
  ) {
    throw new Error('data.json 缺少 generatedAt 或有效 stocks');
  }
  return payload;
}

async function startLocalPreview() {
  await access(path.join(WEB_ROOT, 'dist', 'index.html')).catch(() => {
    throw new Error('未找到 web/dist/index.html，请先运行 npm run build');
  });

  const server = await preview({
    root: WEB_ROOT,
    logLevel: 'warn',
    preview: {
      host: '127.0.0.1',
      port: 4173,
      strictPort: false,
    },
  });
  const address = server.httpServer.address();
  if (!address || typeof address === 'string') {
    await server.close();
    throw new Error('无法确定本地预览地址');
  }
  return {
    server,
    url: `http://127.0.0.1:${address.port}/`,
  };
}

async function saveScreenshot(locator, filePath) {
  await locator.scrollIntoViewIfNeeded();
  await locator.screenshot({
    path: filePath,
    animations: 'disabled',
  });
}

async function captureCharts({ baseUrl, outputRoot, theme }) {
  const dashboard = await loadDashboard(baseUrl);
  const generatedAtStem = safeFileStem(dashboard.generatedAt);
  const outputDirectory = path.join(outputRoot, generatedAtStem);
  await mkdir(outputDirectory, { recursive: true });

  let browser;
  try {
    browser = await chromium.launch({ headless: true });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes('Executable doesn\'t exist') || message.includes('browserType.launch')) {
      throw new Error(
        'Chromium 尚未安装，请先在 apps/dashboard/web 下运行 npx playwright install chromium',
        { cause: error },
      );
    }
    throw error;
  }

  const images = [];
  try {
    const page = await browser.newPage({
      viewport: { width: 1600, height: 1200 },
      deviceScaleFactor: 1,
    });
    await page.addInitScript((selectedTheme) => {
      localStorage.setItem('theme', selectedTheme);
    }, theme);

    await page.goto(baseUrl, { waitUntil: 'networkidle' });
    await page.locator('.overview-section').waitFor({ state: 'visible' });

    const overviewFile = `overview-${generatedAtStem}.png`;
    await saveScreenshot(
      page.locator('.overview-section'),
      path.join(outputDirectory, overviewFile),
    );
    images.push({ kind: 'overview', file: overviewFile });

    for (const stock of dashboard.stocks) {
      if (!stock || typeof stock.code !== 'string' || typeof stock.name !== 'string') {
        continue;
      }
      const codeStem = safeFileStem(stock.code);
      const card = page.locator('.instrument-overview-card').filter({ hasText: stock.code }).first();
      await card.click();
      await page.getByRole('button', { name: '日内工作台', exact: true }).click();
      const workspace = page.locator('.selected-instrument-workspace');
      await workspace.waitFor({ state: 'visible' });

      const dailyPanel = page.locator('.chart-panel').first();
      await dailyPanel.locator('canvas').first().waitFor({ state: 'visible' });

      const workspaceFile = `${codeStem}-workspace-${generatedAtStem}.png`;
      await saveScreenshot(workspace, path.join(outputDirectory, workspaceFile));
      images.push({
        kind: 'workspace',
        code: stock.code,
        name: stock.name,
        file: workspaceFile,
      });

      const dailyFile = `${codeStem}-daily-${generatedAtStem}.png`;
      await saveScreenshot(dailyPanel, path.join(outputDirectory, dailyFile));
      images.push({
        kind: 'daily-chart',
        code: stock.code,
        name: stock.name,
        file: dailyFile,
      });

      if (Array.isArray(stock.intraday) && stock.intraday.length > 0) {
        const intradayPanel = page.locator('.intraday-panel');
        await intradayPanel.locator('canvas').first().waitFor({ state: 'visible' });
        const intradayFile = `${codeStem}-intraday-${generatedAtStem}.png`;
        await saveScreenshot(intradayPanel, path.join(outputDirectory, intradayFile));
        images.push({
          kind: 'intraday-chart',
          code: stock.code,
          name: stock.name,
          file: intradayFile,
        });
      }

      await page.getByRole('button', { name: '盘前概览', exact: true }).click();
      await page.locator('.overview-section').waitFor({ state: 'visible' });
    }
  } finally {
    await browser.close();
  }

  const manifest = buildExportManifest({
    generatedAt: dashboard.generatedAt,
    exportedAt: new Date().toISOString(),
    sourceUrl: baseUrl,
    theme,
    images,
  });
  await writeFile(
    path.join(outputDirectory, 'manifest.json'),
    `${JSON.stringify(manifest, null, 2)}\n`,
    'utf8',
  );
  return { outputDirectory, manifest };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(usage());
    return;
  }

  const outputRoot = options.output
    ? path.resolve(process.cwd(), options.output)
    : DEFAULT_OUTPUT_ROOT;

  let previewServer = null;
  let baseUrl = options.url ? normalizeBaseUrl(options.url) : null;
  try {
    if (!baseUrl) {
      const local = await startLocalPreview();
      previewServer = local.server;
      baseUrl = local.url;
    }

    const result = await captureCharts({
      baseUrl,
      outputRoot,
      theme: options.theme,
    });
    console.log(`图表图片已导出：${result.outputDirectory}`);
    console.log(`图片数量：${result.manifest.images.length}`);
  } finally {
    if (previewServer) {
      await previewServer.close();
    }
  }
}

const directExecution =
  process.argv[1] && pathToFileURL(path.resolve(process.argv[1])).href === import.meta.url;

if (directExecution) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
