import { describe, expect, it } from 'vitest';
import type { Graph, GraphNode } from '$lib/types';
import {
  LANE_GROUP_COLORS,
  bandColor,
  hexToRgba,
  laneAccentColor,
  nodeColor,
} from './laneColors';

const graph: Graph = {
  nodes: [],
  edges: [],
  meta: {
    lanes: [
      { id: 'blood-nation', label: 'Bloods', group: 'Bloods' },
      { id: 'california-crips-other', label: 'Crips', group: 'Crips' },
      { id: 'california-crips-hoover', label: 'Hoover', group: 'Crips' },
      { id: 'chicago-folk', label: 'Folk', group: 'Chicago' },
      { id: 'chicago-people', label: 'People', group: 'Chicago' },
      { id: 'california-latino-east-la', label: 'East LA', group: 'Latino' },
      { id: 'asian-gangs', label: 'Asian', group: 'Asian' },
      { id: 'new-york', label: 'NY', group: 'New York' },
      { id: 'detroit', label: 'Detroit', group: 'Detroit' },
      { id: 'motorcycle-clubs', label: 'MC', group: 'Motorcycle' },
      { id: 'prison', label: 'Prison', group: 'Prison' },
      { id: 'white-supremacist', label: 'WS', group: 'White Supremacist' },
      { id: 'organized-crime', label: 'OC', group: 'Organized Crime' },
      { id: 'midwest', label: 'Midwest', group: 'Regional' },
      { id: 'cybercrime', label: 'Cyber', group: 'Cybercrime' },
      { id: 'unplaced', label: 'Unplaced', group: 'Regional' },
    ],
  },
};

function node(lane: string, nation?: string): GraphNode {
  return {
    id: 'org:x',
    label: 'x',
    data: {
      nation_affiliation: nation,
      layout: {
        lane,
        lane_index: 0,
        display_year: 1980,
        slot: 0,
        overview: false,
      },
    },
  };
}

describe('laneColors', () => {
  it('converts hex to rgba', () => {
    expect(hexToRgba('#e05550', 0.04)).toBe('rgba(224,85,80,0.04)');
  });

  it('uses group hues for bands', () => {
    expect(bandColor('blood-nation', graph)).toBe(hexToRgba(LANE_GROUP_COLORS.Bloods, 0.04));
    expect(bandColor('chicago-folk', graph)).toBe(hexToRgba(LANE_GROUP_COLORS.Chicago, 0.04));
    expect(bandColor('california-latino-east-la', graph)).toBe(hexToRgba(LANE_GROUP_COLORS.Latino, 0.04));
    expect(bandColor('prison', graph)).toBe(hexToRgba(LANE_GROUP_COLORS.Prison, 0.04));
    expect(bandColor('white-supremacist', graph)).toBe(hexToRgba(LANE_GROUP_COLORS['White Supremacist'], 0.04));
  });

  it('leaves unplaced with no band', () => {
    expect(bandColor('unplaced', graph)).toBe('transparent');
  });

  it('paints Hoover orange, other Crips blue', () => {
    expect(laneAccentColor('california-crips-hoover', graph)).toBe('#e09b3d');
    expect(laneAccentColor('california-crips-other', graph)).toBe(LANE_GROUP_COLORS.Crips);
  });

  it('uses the same hex for node and band (except unplaced)', () => {
    const hex = laneAccentColor('detroit', graph);
    expect(nodeColor(node('detroit'), graph)).toBe(hex);
    expect(bandColor('detroit', graph)).toBe(hexToRgba(hex, 0.04));
  });

  it('lets Bloods/Crips nation win unless Hoover override', () => {
    expect(nodeColor(node('new-york', 'org:bloods'), graph)).toBe(LANE_GROUP_COLORS.Bloods);
    expect(nodeColor(node('new-york', 'org:crips'), graph)).toBe(LANE_GROUP_COLORS.Crips);
    expect(nodeColor(node('california-crips-hoover', 'org:crips'), graph)).toBe('#e09b3d');
  });

  it('does not split Chicago Folk / People', () => {
    expect(nodeColor(node('chicago-folk'), graph)).toBe(LANE_GROUP_COLORS.Chicago);
    expect(nodeColor(node('chicago-people'), graph)).toBe(LANE_GROUP_COLORS.Chicago);
  });
});
