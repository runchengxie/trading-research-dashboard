import assert from 'node:assert/strict';
import test from 'node:test';

import { parsePlatformPublication } from './platformPublication.ts';

function manifest() {
  return {
    schema_version: 'research.platform-publication.v1',
    generated_at: '2026-09-02T05:20:00+00:00',
    producer_repository: 'runchengxie/research-workspace',
    producer_commit: 'abc123',
    run_id: 'run-1',
    artifacts: [
      {
        artifact_id: 'strategy.evidence',
        relative_path: 'strategies/evidence.json',
        schema_version: 'strategy.evidence.v1',
        sha256: 'a'.repeat(64),
        media_type: 'application/json',
        audience: 'public',
        consumers: ['trading-research-dashboard'],
      },
      {
        artifact_id: 'intel.operator',
        relative_path: 'intel/operator.json',
        schema_version: 'intel.operator.v1',
        sha256: 'b'.repeat(64),
        media_type: 'application/json',
        audience: 'internal',
        consumers: ['market-intel'],
      },
    ],
  };
}

test('parses public dashboard projections and filters other consumers', () => {
  const parsed = parsePlatformPublication(manifest());
  assert.equal(parsed.producerRepository, 'runchengxie/research-workspace');
  assert.equal(parsed.artifacts.length, 1);
  assert.equal(parsed.artifacts[0].artifactId, 'strategy.evidence');
});

test('rejects internal projection targeted at public dashboard', () => {
  const value = manifest();
  value.artifacts[1].consumers = ['trading-research-dashboard'];
  assert.throws(() => parsePlatformPublication(value), /internal/);
});

test('rejects unsafe projection path', () => {
  const value = manifest();
  value.artifacts[0].relative_path = '../private/model.bin';
  assert.throws(() => parsePlatformPublication(value), /relative_path/);
});

test('rejects malformed sha256', () => {
  const value = manifest();
  value.artifacts[0].sha256 = 'abc';
  assert.throws(() => parsePlatformPublication(value), /sha256/);
});
