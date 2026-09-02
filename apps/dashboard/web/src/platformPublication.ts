export const PLATFORM_PUBLICATION_SCHEMA = 'research.platform-publication.v1';
export const DASHBOARD_PUBLICATION_CONSUMER = 'trading-research-dashboard';

export interface PlatformPublicationArtifact {
  artifactId: string;
  relativePath: string;
  schemaVersion: string;
  sha256: string;
  mediaType: string;
  audience: 'public';
}

export interface PlatformPublication {
  generatedAt: string;
  producerRepository: string;
  producerCommit: string;
  runId: string;
  artifacts: PlatformPublicationArtifact[];
}

export type PlatformPublicationLoadResult =
  | { status: 'available'; publication: PlatformPublication; error: null }
  | { status: 'missing'; publication: null; error: null }
  | { status: 'error'; publication: null; error: string };

type JsonRecord = Record<string, unknown>;

function record(value: unknown, field: string): JsonRecord {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new Error(`${field} must be an object`);
  }
  return value as JsonRecord;
}

function text(value: unknown, field: string): string {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`${field} must be a non-empty string`);
  }
  return value.trim();
}

function safeRelativePath(value: unknown): string {
  const path = text(value, 'relative_path');
  if (
    path.startsWith('/') ||
    path.includes('\\') ||
    path.split('/').some((segment) => segment === '' || segment === '.' || segment === '..')
  ) {
    throw new Error('relative_path must be a safe POSIX relative path');
  }
  return path;
}

function consumers(value: unknown, field: string): string[] {
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error(`${field} must be a non-empty list`);
  }
  const normalized = value.map((item, index) => text(item, `${field}[${index}]`));
  if (new Set(normalized).size !== normalized.length) {
    throw new Error(`${field} must contain unique values`);
  }
  return normalized;
}

function sha256(value: unknown, field: string): string {
  const digest = text(value, field);
  if (!/^[0-9a-f]{64}$/.test(digest)) {
    throw new Error(`${field} must be a lowercase sha256 digest`);
  }
  return digest;
}

export function parsePlatformPublication(value: unknown): PlatformPublication {
  const payload = record(value, 'platform publication');
  const schemaVersion = text(payload.schema_version, 'schema_version');
  if (schemaVersion !== PLATFORM_PUBLICATION_SCHEMA) {
    throw new Error(`unsupported platform publication schema: ${schemaVersion}`);
  }
  if (!Array.isArray(payload.artifacts)) {
    throw new Error('artifacts must be a list');
  }

  const selected: PlatformPublicationArtifact[] = [];
  const seenIds = new Set<string>();
  const seenPaths = new Set<string>();
  payload.artifacts.forEach((rawArtifact, index) => {
    const artifact = record(rawArtifact, `artifacts[${index}]`);
    const artifactId = text(artifact.artifact_id, `artifacts[${index}].artifact_id`);
    const relativePath = safeRelativePath(artifact.relative_path);
    if (seenIds.has(artifactId)) throw new Error(`duplicate artifact_id: ${artifactId}`);
    if (seenPaths.has(relativePath)) throw new Error(`duplicate relative_path: ${relativePath}`);
    seenIds.add(artifactId);
    seenPaths.add(relativePath);

    const artifactConsumers = consumers(artifact.consumers, `artifacts[${index}].consumers`);
    if (!artifactConsumers.includes(DASHBOARD_PUBLICATION_CONSUMER)) return;

    const audience = text(artifact.audience, `artifacts[${index}].audience`);
    if (audience === 'internal') {
      throw new Error(`internal artifact targeted at public dashboard: ${artifactId}`);
    }
    if (audience !== 'public') {
      throw new Error(`unsupported artifact audience: ${audience}`);
    }

    selected.push({
      artifactId,
      relativePath,
      schemaVersion: text(artifact.schema_version, `artifacts[${index}].schema_version`),
      sha256: sha256(artifact.sha256, `artifacts[${index}].sha256`),
      mediaType: text(artifact.media_type, `artifacts[${index}].media_type`),
      audience: 'public',
    });
  });

  return {
    generatedAt: text(payload.generated_at, 'generated_at'),
    producerRepository: text(payload.producer_repository, 'producer_repository'),
    producerCommit: text(payload.producer_commit, 'producer_commit'),
    runId: text(payload.run_id, 'run_id'),
    artifacts: selected,
  };
}

export async function loadPlatformPublication(): Promise<PlatformPublicationLoadResult> {
  try {
    const response = await fetch('./platform-publication.json');
    if (response.status === 404) {
      return { status: 'missing', publication: null, error: null };
    }
    if (!response.ok) {
      throw new Error(`加载平台研究证据清单失败：HTTP ${response.status}`);
    }
    const contentType = response.headers.get('content-type') ?? '';
    if (!contentType.toLowerCase().includes('application/json')) {
      return { status: 'missing', publication: null, error: null };
    }
    return {
      status: 'available',
      publication: parsePlatformPublication(await response.json()),
      error: null,
    };
  } catch (error) {
    return {
      status: 'error',
      publication: null,
      error: error instanceof Error ? error.message : String(error),
    };
  }
}
