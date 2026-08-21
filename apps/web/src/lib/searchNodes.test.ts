import { describe, expect, it } from 'vitest';
import { searchOrgNodes } from './searchNodes';
import type { GraphNode } from './types';

const nodes: GraphNode[] = [
  {
    id: 'org:inglewood-family-gang',
    label: 'Inglewood Family Gang',
    data: {
      standard_name: 'Inglewood Family Gang',
      aliases: ['IF', 'IFG'],
      metro: 'Inglewood',
    },
  },
  {
    id: 'org:cross-atlantic-pirus',
    label: 'Cross Atlantic Pirus',
    data: {
      standard_name: 'Cross Atlantic Pirus',
      aliases: ['CAP'],
      metro: 'Los Angeles',
    },
  },
];

describe('searchOrgNodes', () => {
  it('returns empty for short queries', () => {
    expect(searchOrgNodes(nodes, 'i')).toEqual([]);
  });

  it('matches display name', () => {
    const hits = searchOrgNodes(nodes, 'inglewood');
    expect(hits[0]?.node.id).toBe('org:inglewood-family-gang');
  });

  it('matches aliases', () => {
    const hits = searchOrgNodes(nodes, 'ifg');
    expect(hits[0]?.node.id).toBe('org:inglewood-family-gang');
    expect(hits[0]?.matchField).toBe('alias');
  });

  it('matches slug id', () => {
    const hits = searchOrgNodes(nodes, 'cross atlantic');
    expect(hits[0]?.node.id).toBe('org:cross-atlantic-pirus');
  });
});
