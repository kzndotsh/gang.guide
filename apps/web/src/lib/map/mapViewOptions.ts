import type { EdgeMode } from '$lib/map/KonvaMap.svelte';

export type EdgeOption = {
  value: EdgeMode;
  label: string;
  hint: string;
  needsSelection?: boolean;
};

export const EDGE_OPTIONS: EdgeOption[] = [
  {
    value: 'hover',
    label: 'On hover',
    hint: 'Edges appear only when hovering or selecting a node.',
  },
  {
    value: 'all',
    label: 'All links',
    hint: 'Every alliance, rivalry, and affiliation on the map.',
  },
];

export function edgeHint(mode: EdgeMode): string {
  return EDGE_OPTIONS.find((o) => o.value === mode)?.hint ?? '';
}
