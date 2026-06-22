import type { EdgeMode } from '$lib/map/KonvaMap.svelte';

export type EdgeOption = {
  value: EdgeMode;
  label: string;
  hint: string;
  needsSelection?: boolean;
};

export const EDGE_OPTIONS: EdgeOption[] = [
  {
    value: 'nation',
    label: 'Nation ties',
    hint: 'Only nation-affiliation lines (set → Folk/People/Bloods/Crips, etc.).',
  },
  {
    value: 'focus',
    label: 'Selected',
    hint: 'All connection types for the org you clicked.',
    needsSelection: true,
  },
  {
    value: 'all',
    label: 'All links',
    hint: 'Every alliance, rivalry, and affiliation on the map (default).',
  },
];

export function edgeHint(mode: EdgeMode): string {
  return EDGE_OPTIONS.find((o) => o.value === mode)?.hint ?? '';
}
