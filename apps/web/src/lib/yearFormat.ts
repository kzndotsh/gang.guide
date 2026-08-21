import type { GraphNode, YearPrecision } from '$lib/types';
export type { YearPrecision } from '$lib/types';

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

function yearSpanFromNodeData(
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

function yearSpanFromLayout(data: GraphNode['data'] | undefined): YearSpan | null {
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
  if (typeof data?.disbanded_year === 'number') {
    return {
      earliest: data.disbanded_year,
      latest: data.disbanded_year,
      precision: 'exact',
      midpoint: data.disbanded_year,
    };
  }
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
