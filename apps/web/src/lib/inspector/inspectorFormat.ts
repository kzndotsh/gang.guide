import type { OrganizationStatus } from '$lib/types';

const ORG_TYPE_LABELS: Record<string, string> = {
  nation: 'Nation',
  alliance: 'Alliance',
  car: 'Car',
  set: 'Set',
  faction: 'Faction',
  prison_gang: 'Prison gang',
  other: 'Organization',
};

const REL_TYPE_LABELS: Record<string, string> = {
  spin_off: 'Spin-off',
  parent_set: 'Parent set',
  parent: 'Parent',
  member_of: 'Member of',
  offspring: 'Offspring',
  nation: 'Nation',
  alliance: 'Alliance',
  rivalry: 'Rivalry',
  truce: 'Truce',
  migration: 'Migration',
  merger: 'Merger',
  split: 'Split',
  car_affiliation: 'Car affiliation',
  nation_affiliation: 'Nation',
  influence: 'Influence',
  other: 'Related',
};

const STATUS_LABELS: Record<OrganizationStatus, string> = {
  active: 'Active',
  inactive: 'Inactive',
  defunct: 'Defunct',
  unknown: 'Unknown',
};

const REVIEW_LABELS: Record<string, string> = {
  auto_published: 'Published',
  unverified: 'Unverified',
  needs_agent: 'Needs review',
  pending: 'Pending',
  rejected: 'Rejected',
};

const COLOR_MAP: Record<string, string> = {
  red: '#f85149',
  blue: '#58a6ff',
  green: '#3fb950',
  black: '#1f2328',
  white: '#e6edf3',
  gold: '#d4a72c',
  yellow: '#e3b341',
  orange: '#f0883e',
  purple: '#a371f7',
  brown: '#8b5a2b',
  gray: '#8b949e',
  grey: '#8b949e',
  pink: '#f778ba',
};

export function orgTypeLabel(type: string | undefined): string {
  if (!type) return 'Organization';
  return ORG_TYPE_LABELS[type] ?? type.replace(/_/g, ' ');
}

export function relTypeLabel(type: string): string {
  return REL_TYPE_LABELS[type] ?? type.replace(/_/g, ' ');
}

/** Direction-aware label: shows the relationship from the viewer's perspective.
 *  isOutgoing=true means current node is SOURCE (e.g. Pirus --parent--> Bloods → "Parent of")
 *  isOutgoing=false means current node is TARGET (e.g. Pirus is TARGET of --spin_off--> → "Spawned from")
 */
export function relTypeLabelDirectional(type: string, isOutgoing: boolean | undefined): string {
  if (isOutgoing === undefined) return relTypeLabel(type);
  if (isOutgoing) {
    // Current node is the source — describe what it IS to the peer
    const outLabels: Record<string, string> = {
      parent: 'Parent of',
      member_of: 'Member of',
      spin_off: 'Spawned',
      parent_set: 'Parent set of',
      offspring: 'Spawned',
      merger: 'Merged into',
      split: 'Split from',
      migration: 'Migrated to',
    };
    return outLabels[type] ?? relTypeLabel(type);
  } else {
    // Current node is the target — describe what the peer IS to it
    const inLabels: Record<string, string> = {
      parent: 'Child org',
      member_of: 'Has member',
      spin_off: 'Spun off from this',
      parent_set: 'Child set',
      offspring: 'Offspring of this',
      merger: 'Merged from',
      split: 'Split into',
      migration: 'Migrated from',
    };
    return inLabels[type] ?? relTypeLabel(type);
  }
}

export function statusLabel(status: OrganizationStatus | undefined): string | null {
  if (!status || status === 'unknown') return null;
  return STATUS_LABELS[status];
}

export function reviewLabel(status: string | undefined): string {
  if (!status) return 'Unknown';
  return REVIEW_LABELS[status] ?? status.replace(/_/g, ' ');
}

export function colorSwatch(name: string): string {
  const key = name.trim().toLowerCase();
  return COLOR_MAP[key] ?? '#484f58';
}

export function truncate(text: string, max = 140): string {
  const clean = text.replace(/\s+/g, ' ').trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1)}…`;
}

export function confidencePct(score: number | undefined): string | null {
  if (score == null) return null;
  return `${Math.round(score * 100)}%`;
}
