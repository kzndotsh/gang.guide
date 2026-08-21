import { describe, expect, it } from 'vitest';
import { isUsableStageSize } from './panZoom';

describe('isUsableStageSize', () => {
  it('rejects an unlaid-out container', () => {
    expect(isUsableStageSize(0, 0)).toBe(false);
    expect(isUsableStageSize(390, 0)).toBe(false);
  });

  it('accepts a laid-out mobile viewport', () => {
    expect(isUsableStageSize(390, 700)).toBe(true);
  });
});
