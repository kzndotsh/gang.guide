import type { Graph, GraphNode } from '$lib/types';
import { laneCatalog } from './layout';

/** Group identity hues. Same hex for node fill and lane band (band at 4% alpha). */
export const LANE_GROUP_COLORS: Record<string, string> = {
  Bloods: '#e05550',
  Crips: '#4a9eff',
  Chicago: '#3fb950',
  Latino: '#d29922',
  Asian: '#bc8ff3',
  'New York': '#da7756',
  Detroit: '#c47a5a',
  Motorcycle: '#8b949e',
  Prison: '#6e7f9a',
  'White Supremacist': '#8a8f6e',
  'Organized Crime': '#5c6b7a',
  Regional: '#6e7681',
  Cybercrime: '#3d9b8f',
};

/** Hoover dropped Crip blue; only this lane is orange. */
export const LANE_COLOR_OVERRIDES: Record<string, string> = {
  'california-crips-hoover': '#e09b3d',
};

const NO_BAND_LANES = new Set(['unplaced']);
const BAND_ALPHA = 0.04;
const FALLBACK_HEX = LANE_GROUP_COLORS.Regional;

export function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '');
  const n = Number.parseInt(h, 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r},${g},${b},${alpha})`;
}

export function laneGroup(laneId: string, graph?: Graph): string | undefined {
  return laneCatalog(graph).find((l) => l.id === laneId)?.group;
}

export function laneAccentColor(laneId: string, graph?: Graph): string {
  const override = LANE_COLOR_OVERRIDES[laneId];
  if (override) return override;
  const group = laneGroup(laneId, graph);
  if (!group) return FALLBACK_HEX;
  return LANE_GROUP_COLORS[group] ?? FALLBACK_HEX;
}

export function bandColor(laneId: string, graph?: Graph): string {
  if (NO_BAND_LANES.has(laneId)) return 'transparent';
  return hexToRgba(laneAccentColor(laneId, graph), BAND_ALPHA);
}

export function nodeColor(node: GraphNode, graph?: Graph): string {
  const lane = node.data?.layout?.lane ?? 'unplaced';
  if (LANE_COLOR_OVERRIDES[lane]) return LANE_COLOR_OVERRIDES[lane];
  const nation = node.data?.nation_affiliation;
  if (nation === 'org:bloods') return LANE_GROUP_COLORS.Bloods;
  if (nation === 'org:crips') return LANE_GROUP_COLORS.Crips;
  return laneAccentColor(lane, graph);
}
