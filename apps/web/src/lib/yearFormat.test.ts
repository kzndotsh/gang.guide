import { describe, expect, it } from 'vitest';
import { formatYearSpan, resolveDissolvedYearSpan, resolveNodeYearSpan } from './yearFormat';

describe('yearFormat', () => {
  it('formats founded years with precision', () => {
    expect(resolveNodeYearSpan({ founded_year: 1957, founded_year_precision: 'exact' })).toMatchObject({
      earliest: 1957,
      precision: 'exact',
    });
    expect(formatYearSpan({ earliest: 1960, latest: 1960, precision: 'circa' })).toBe('circa 1960');
  });

  it('uses disbanded_year for dissolve span', () => {
    const span = resolveDissolvedYearSpan({ disbanded_year: 2005 });
    expect(span).toMatchObject({ earliest: 2005, latest: 2005, precision: 'exact' });
    expect(formatYearSpan(span!)).toBe('2005');
  });
});
