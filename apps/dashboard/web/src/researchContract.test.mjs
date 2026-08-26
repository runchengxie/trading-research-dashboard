import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

import { adaptNiuMenSnapshot } from './research/niuMenAdapter.ts';
import { parseResearchSnapshot } from './researchSnapshot.ts';

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const SCHEMA_PATH = path.join(REPO_ROOT, 'schemas', 'research-snapshot.schema.json');

function readJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(REPO_ROOT, relativePath), 'utf8'));
}

async function validateJson(relativePath) {
  const { default: Ajv2020 } = await import('ajv/dist/2020.js');
  const ajv = new Ajv2020({ allErrors: true, strict: true });
  const validate = ajv.compile(JSON.parse(fs.readFileSync(SCHEMA_PATH, 'utf8')));
  const payload = readJson(relativePath);
  const valid = validate(payload);
  return { payload, valid, errors: validate.errors };
}

function validationMessage(relativePath, errors) {
  return `${relativePath}: ${JSON.stringify(errors)}`;
}

test('valid v2 fixture matches the canonical schema', async () => {
  const fixture = 'tests/fixtures/research_snapshot/valid_v2.json';
  assert.equal(fs.existsSync(SCHEMA_PATH), true);
  assert.equal(fs.existsSync(path.join(REPO_ROOT, fixture)), true);

  const result = await validateJson(fixture);

  assert.equal(result.valid, true, validationMessage(fixture, result.errors));
});

test('warning v2 fixture preserves warning and unknown freshness semantics', async () => {
  const fixture = 'tests/fixtures/research_snapshot/warning_v2.json';
  const result = await validateJson(fixture);
  assert.equal(result.valid, true, validationMessage(fixture, result.errors));

  const snapshot = parseResearchSnapshot(result.payload);
  const normalized = adaptNiuMenSnapshot(snapshot, '2026-08-26');

  assert.equal(normalized.quality, 'warning');
  assert.equal(normalized.freshness, 'unknown');
  assert.equal(normalized.provenance.researchCommit, null);
});

test('missing required fields are rejected by the canonical schema', async () => {
  const fixture = 'tests/fixtures/research_snapshot/invalid_missing_required.json';
  const result = await validateJson(fixture);

  assert.equal(result.valid, false);
  assert.ok(result.errors?.length);
});

test('unsupported versions are rejected by schema and parser', async () => {
  const fixture = 'tests/fixtures/research_snapshot/unsupported_version.json';
  const result = await validateJson(fixture);

  assert.equal(result.valid, false);
  assert.throws(
    () => parseResearchSnapshot(result.payload),
    /不支持的研究快照版本/,
  );
});

test('published Dashboard research snapshot matches the canonical schema', async () => {
  const fixture = 'web/public/research.json';
  const result = await validateJson(fixture);

  assert.equal(result.valid, true, validationMessage(fixture, result.errors));
  assert.equal(parseResearchSnapshot(result.payload).schemaVersion, 'niu_men.research_snapshot.v2');
});
