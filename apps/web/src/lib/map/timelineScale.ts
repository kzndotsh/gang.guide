import type { GraphNode } from '$lib/types';
import { deriveClientLayout } from './layout';
import { resolveNodeYearSpan } from '$lib/yearFormat';

/** Pixels between consecutive years on the timeline axis. */
export const PX_PER_YEAR = 42;

/** Sub-year horizontal spread per slot index (sync with packages/map_layout.py). */
export const SLOT_YEAR_OFFSET = 2.4;

/** Rows per column before advancing horizontally (sync with packages/map_layout.py). */
export const LANE_ROW_COUNT = 5;

/** Extra years padded on each side of the visible data range. */
export const YEAR_DOMAIN_PAD = 6;

export const TIMELINE_PAD = 80;

export type TimelineScale = {
  minYear: number;
  maxYear: number;
  pxPerYear: number;
  pad: number;
  svgWidth: number;
  xForYear: (year: number) => number;
};

export function plotYearForNode(node: GraphNode): number {
  const layout = node.data?.layout ?? deriveClientLayout(node);
  return layout.display_year;
}

export function yearsForNode(node: GraphNode): number[] {
  const years: number[] = [];
  const span = resolveNodeYearSpan(node.data);
  if (span) {
    years.push(span.earliest, span.latest);
    if (span.midpoint != null) years.push(span.midpoint);
  }
  const layout = node.data?.layout ?? deriveClientLayout(node);
  years.push(layout.display_year);
  years.push(plotYearForNode(node));
  return years;
}

export function computeYearDomain(
  nodes: GraphNode[],
  yearPad = YEAR_DOMAIN_PAD
): { minYear: number; maxYear: number } {
  const years = nodes.flatMap(yearsForNode);
  if (!years.length) {
    return { minYear: 1955, maxYear: 2025 };
  }
  return {
    minYear: Math.floor(Math.min(...years)) - yearPad,
    maxYear: Math.ceil(Math.max(...years)) + yearPad,
  };
}

export function buildTimelineScale(
  minYear: number,
  maxYear: number,
  pad = TIMELINE_PAD,
  pxPerYear = PX_PER_YEAR
): TimelineScale {
  const span = Math.max(maxYear - minYear, 1);
  const svgWidth = pad * 2 + span * pxPerYear;
  const xForYear = (year: number) => pad + (year - minYear) * pxPerYear;
  return { minYear, maxYear, pxPerYear, pad, svgWidth, xForYear };
}

/** Every calendar year in the domain — one tick per year. */
export function yearTicks(minYear: number, maxYear: number): number[] {
  const ticks: number[] = [];
  for (let y = minYear; y <= maxYear; y += 1) ticks.push(y);
  return ticks;
}

/** Label cadence: every year when zoomed in, otherwise every 5th year. */
export function labeledYearStep(spanYears: number): number {
  if (spanYears <= 30) return 1;
  if (spanYears <= 60) return 5;
  return 10;
}

export function labeledYears(minYear: number, maxYear: number, step: number): number[] {
  if (step <= 1) return yearTicks(minYear, maxYear);
  const start = Math.ceil(minYear / step) * step;
  const ticks: number[] = [];
  for (let y = start; y <= maxYear; y += step) ticks.push(y);
  return ticks;
}
