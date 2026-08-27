import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

test('Dashboard root declares the editorial research shell', () => {
  const source = readFileSync(join(here, 'App.tsx'), 'utf8');

  assert.match(source, /className="container editorial-dashboard"/);
});
