import { describe, expect, it } from 'vitest';
import { DEFAULT_YEAR_MIN, yearQueryValue } from './urlState';

describe('yearQueryValue', () => {
  it('omits the default 1930→domain-max range so `/` is not rewritten on first load', () => {
    expect(yearQueryValue(DEFAULT_YEAR_MIN, 2025, 2025)).toBeNull();
  });

  it('writes a narrowed range', () => {
    expect(yearQueryValue(1930, 1980, 2025)).toBe('1930-1980');
  });

  it('writes when max is the calendar year instead of the graph max', () => {
    expect(yearQueryValue(1930, 2026, 2025)).toBe('1930-2026');
  });
});