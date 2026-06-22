import type { GraphEdge } from '$lib/types';

/** Relationship types stored in both directions in the graph export. */
const SYMMETRIC_REL_TYPES = new Set(['rivalry', 'alliance', 'truce']);

export type ConnectionRow = {
  type: string;
  peerId: string;
  confidenceScore?: number;
  reviewStatus?: string;
};

export type ConnectionGroup = {
  id: string;
  label: string;
  items: ConnectionRow[];
};

const CONNECTION_GROUP_DEFS: Array<{ id: string; label: string; types: string[] }> = [
  { id: 'affiliation', label: 'Affiliations', types: ['nation_affiliation', 'car_affiliation'] },
  { id: 'alliance', label: 'Alliances', types: ['alliance', 'truce'] },
  { id: 'rivalry', label: 'Rivalries', types: ['rivalry'] },
  {
    id: 'structure',
    label: 'Structure',
    types: ['parent_set', 'spin_off', 'offspring', 'merger', 'split', 'migration'],
  },
  { id: 'other', label: 'Other', types: ['influence', 'other'] },
];

const TYPE_TO_GROUP = new Map<string, string>(
  CONNECTION_GROUP_DEFS.flatMap((g) => g.types.map((t) => [t, g.id] as const)),
);

function connectionKey(nodeId: string, edge: GraphEdge, peerId: string): string {
  if (SYMMETRIC_REL_TYPES.has(edge.type)) {
    const pair = [nodeId, peerId].sort().join('\0');
    return `${edge.type}:${pair}`;
  }
  return `${edge.type}:${peerId}`;
}

function pickBetter(existing: ConnectionRow, edge: GraphEdge, peerId: string): ConnectionRow {
  const score = edge.confidence_score ?? 0;
  const existingScore = existing.confidenceScore ?? 0;
  if (score > existingScore) {
    return {
      type: edge.type,
      peerId,
      confidenceScore: edge.confidence_score,
      reviewStatus: edge.review_status,
    };
  }
  if (!existing.reviewStatus && edge.review_status) {
    return { ...existing, reviewStatus: edge.review_status };
  }
  return existing;
}

/** One row per logical connection; merges mirrored rivalry/alliance edges. */
export function mergeConnections(nodeId: string, edges: GraphEdge[]): ConnectionRow[] {
  const map = new Map<string, ConnectionRow>();

  for (const edge of edges) {
    if (edge.source !== nodeId && edge.target !== nodeId) continue;
    const peerId = edge.source === nodeId ? edge.target : edge.source;
    const key = connectionKey(nodeId, edge, peerId);
    const existing = map.get(key);
    map.set(
      key,
      existing ? pickBetter(existing, edge, peerId) : {
        type: edge.type,
        peerId,
        confidenceScore: edge.confidence_score,
        reviewStatus: edge.review_status,
      },
    );
  }

  return [...map.values()];
}

/** Drop alliance/truce rows when the same peer is already a rivalry. */
export function dropConflictingSoftTies(rows: ConnectionRow[]): ConnectionRow[] {
  const rivalryPeers = new Set(rows.filter((r) => r.type === 'rivalry').map((r) => r.peerId));
  return rows.filter((r) => {
    if (r.type === 'alliance' || r.type === 'truce') {
      return !rivalryPeers.has(r.peerId);
    }
    return true;
  });
}

export function sortConnections(
  rows: ConnectionRow[],
  labelFor: (id: string) => string,
): ConnectionRow[] {
  return [...rows].sort((a, b) => labelFor(a.peerId).localeCompare(labelFor(b.peerId)));
}

export function groupConnections(
  rows: ConnectionRow[],
  labelFor: (id: string) => string,
): ConnectionGroup[] {
  const buckets = new Map<string, ConnectionRow[]>();
  for (const def of CONNECTION_GROUP_DEFS) {
    buckets.set(def.id, []);
  }

  for (const row of rows) {
    const groupId = TYPE_TO_GROUP.get(row.type) ?? 'other';
    buckets.get(groupId)?.push(row);
  }

  return CONNECTION_GROUP_DEFS.map((def) => ({
    id: def.id,
    label: def.label,
    items: sortConnections(buckets.get(def.id) ?? [], labelFor),
  })).filter((g) => g.items.length > 0);
}
