import type { GraphNode } from './types';

export type YearPrecision = 'exact' | 'circa' | 'decade' | 'range';

export type YearSpan = {
  earliest: number;
  latest: number;
  precision: YearPrecision;
  midpoint?: number;
};

type YearPrefix = 'founded' | 'dissolved';

function yearField(data: GraphNode['data'] | undefined, prefix: YearPrefix, suffix: string): unknown {
  if (!data) return undefined;
  const key = `${prefix}_${suffix}` as keyof GraphNode['data'];
  return data[key];
}

export function yearSpanFromNodeData(
  data: GraphNode['data'] | undefined,
  prefix: YearPrefix = 'founded',
): YearSpan | null {
  const earliest = yearField(data, prefix, 'year');
  if (typeof earliest !== 'number') return null;
  const latestRaw = yearField(data, prefix, 'year_latest');
  const latest = typeof latestRaw === 'number' ? latestRaw : earliest;
  const precisionRaw = yearField(data, prefix, 'year_precision');
  const precision = (typeof precisionRaw === 'string' ? precisionRaw : 'exact') as YearPrecision;
  return {
    earliest,
    latest,
    precision,
    midpoint: Math.floor((earliest + latest) / 2),
  };
}

export function yearSpanFromLayout(data: GraphNode['data'] | undefined): YearSpan | null {
  const layoutSpan = data?.layout?.year_span;
  if (!layoutSpan) return null;
  return {
    earliest: layoutSpan.earliest,
    latest: layoutSpan.latest,
    precision: layoutSpan.precision as YearPrecision,
    midpoint: layoutSpan.midpoint,
  };
}

export function resolveNodeYearSpan(data: GraphNode['data'] | undefined): YearSpan | null {
  return yearSpanFromNodeData(data, 'founded') ?? yearSpanFromLayout(data);
}

export function resolveDissolvedYearSpan(data: GraphNode['data'] | undefined): YearSpan | null {
  return yearSpanFromNodeData(data, 'dissolved');
}

export function formatYearSpan(span: YearSpan): string {
  const { earliest, latest, precision } = span;
  if (precision === 'circa') return `circa ${earliest}`;
  if (precision === 'decade') {
    if (latest - earliest >= 9) return `~${Math.floor(earliest / 10) * 10}s`;
    return `~${earliest}–${latest}`;
  }
  if (precision === 'range' || latest !== earliest) return `~${earliest}–${latest}`;
  return String(earliest);
}

export function eventYearMidpoint(ev: {
  year?: number | null;
  year_earliest?: number | null;
  year_latest?: number | null;
}): number | null {
  if (ev.year_earliest != null) {
    const hi = ev.year_latest ?? ev.year_earliest;
    return Math.floor((ev.year_earliest + hi) / 2);
  }
  return ev.year ?? null;
}

export function formatEventYear(ev: {
  year?: number | null;
  year_earliest?: number | null;
  year_latest?: number | null;
  year_precision?: YearPrecision | null;
}): string {
  if (ev.year_earliest != null) {
    return formatYearSpan({
      earliest: ev.year_earliest,
      latest: ev.year_latest ?? ev.year_earliest,
      precision: ev.year_precision ?? (ev.year_latest !== ev.year_earliest ? 'range' : 'exact'),
    });
  }
  if (ev.year != null) return String(ev.year);
  return 'undated';
}

export function spanHasBand(span: YearSpan): boolean {
  return span.precision === 'decade' || span.precision === 'range' || span.latest !== span.earliest;
}
