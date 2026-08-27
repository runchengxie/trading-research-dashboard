import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

test('editorial stylesheet defines the research-paper visual system', () => {
  const path = join(here, 'editorial.css');
  assert.equal(existsSync(path), true, 'editorial.css must exist');

  const source = readFileSync(path, 'utf8');
  assert.match(source, /--editorial-paper:/);
  assert.match(source, /--editorial-grid:/);
  assert.match(source, /\.section-nav\s*\{/);
  assert.match(source, /\.instrument-overview-card\s*\{/);
  assert.match(source, /box-shadow:\s*none/);
});
