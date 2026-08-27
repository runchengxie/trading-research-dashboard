import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

test('Dashboard loads the editorial research shell after the base stylesheet', () => {
  const source = readFileSync(join(here, 'main.tsx'), 'utf8');

  assert.match(source, /import '\.\/styles\.css';\s*import '\.\/editorial\.css';/);
});
