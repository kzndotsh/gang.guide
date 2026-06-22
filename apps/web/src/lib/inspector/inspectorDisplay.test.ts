import { describe, expect, it } from 'vitest';
import { orgDisplayDescription, orgDisplayTitle } from '$lib/inspector/inspectorDisplay';
import type { GraphNode } from '$lib/types';

const crossAtlantic: GraphNode = {
  id: 'org:cross-atlantic-pirus',
  type: 'organization',
  label: 'Cross Atlantic Pirus (Eastside Compton / Lynwood) Cross Atlantic Pirus',
  detail_level: 'skeleton',
  review_status: 'auto',
  data: {
    standard_name: 'Cross Atlantic Pirus',
    description:
      'Cross Atlantic Pirus (Eastside Compton / Lynwood) Cross Atlantic Pirus are a predominately African-American street gang located in the border area of the cities of Lynwood and Compton',
  },
};

describe('orgDisplayTitle', () => {
  it('prefers data.standard_name over export label', () => {
    expect(orgDisplayTitle(crossAtlantic)).toBe('Cross Atlantic Pirus');
  });

  it('deduplicates repeated name in label fallback', () => {
    const node: GraphNode = {
      id: 'org:52-broadway-gangster-crips-los-angeles',
      type: 'organization',
      label: '52 Broadway Gangster Crips Broadway Gangster Crips The Five Deuce BGCs',
      detail_level: 'skeleton',
      review_status: 'auto',
      data: {},
    };
    expect(orgDisplayTitle(node)).toBe('52 Broadway Gangster Crips');
  });

  it('deduplicates exact-repeat name', () => {
    const node: GraphNode = {
      id: 'org:center-view-piru',
      type: 'organization',
      label: 'Center View Piru Center View Piru',
      detail_level: 'skeleton',
      review_status: 'auto',
      data: {},
    };
    expect(orgDisplayTitle(node)).toBe('Center View Piru');
  });

  it('strips geo parenthetical between repeated segments', () => {
    const node: GraphNode = {
      id: 'org:cross-atlantic-pirus',
      type: 'organization',
      label: 'Cross Atlantic Pirus (Eastside Compton / Lynwood) Compton Cross Atlantic Pirus',
      detail_level: 'skeleton',
      review_status: 'auto',
      data: {},
    };
    expect(orgDisplayTitle(node)).toBe('Cross Atlantic Pirus');
  });
});

describe('orgDisplayDescription', () => {
  it('strips duplicated StreetGangs title lead-in', () => {
    expect(orgDisplayDescription(crossAtlantic)).toBe(
      'Cross Atlantic Pirus are a predominately African-American street gang located in the border area of the cities of Lynwood and Compton',
    );
  });
});
