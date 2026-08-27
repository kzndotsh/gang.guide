import type { EdgeMode } from '$lib/map/KonvaMap.svelte';

export type EdgeOption = {
  value: EdgeMode;
  label: string;
  /** Shorter touch UI label (no hover on mobile). */
  mobileLabel: string;
  hint: string;
  needsSelection?: boolean;
};

export const EDGE_OPTIONS: EdgeOption[] = [
  {
    value: 'hover',
    label: 'On hover',
    mobileLabel: 'Selected',
    hint: 'Edges appear only when hovering or selecting a node.',
  },
  {
    value: 'all',
    label: 'All links',
    mobileLabel: 'All',
    hint: 'Every alliance, rivalry, and affiliation on the map.',
  },
];
