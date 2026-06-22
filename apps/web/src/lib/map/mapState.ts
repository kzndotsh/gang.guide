/**
 * Map state: zoom commands, year filter, hidden lanes.
 * Extracted from +page.svelte for reusability and separation of concerns.
 */

import type { EdgeMode } from '$lib/map/KonvaMap.svelte';

export type ZoomAction = 'in' | 'out' | 'fit' | 'focus';
export type ZoomCommand = { action: ZoomAction; target?: string; seq: number } | null;

export function createMapState() {
  let zoomCmd = $state<ZoomCommand>(null);
  let zoomSeq = 0;
  let zoomPct = $state(100);
  let yearMin = $state(1930);
  let yearMax = $state(2025);
  let edgeMode = $state<EdgeMode>('all');
  let hiddenLanes = $state<Set<string>>(new Set());

  function sendZoom(action: ZoomAction, target?: string) {
    zoomCmd = { action, target, seq: ++zoomSeq };
  }

  function setZoomPct(pct: number) {
    zoomPct = pct;
  }

  function toggleLaneGroup(lanes: string[]) {
    const allHidden = lanes.every((l) => hiddenLanes.has(l));
    const next = new Set(hiddenLanes);
    for (const l of lanes) {
      if (allHidden) next.delete(l);
      else next.add(l);
    }
    hiddenLanes = next;
  }

  function showAll() {
    hiddenLanes = new Set();
  }

  function hideAll(allLanes: string[]) {
    hiddenLanes = new Set(allLanes);
  }

  return {
    get zoomCmd() { return zoomCmd; },
    get zoomPct() { return zoomPct; },
    get yearMin() { return yearMin; },
    set yearMin(v: number) { yearMin = v; },
    get yearMax() { return yearMax; },
    set yearMax(v: number) { yearMax = v; },
    get edgeMode() { return edgeMode; },
    set edgeMode(v: EdgeMode) { edgeMode = v; },
    get hiddenLanes() { return hiddenLanes; },
    sendZoom,
    setZoomPct,
    toggleLaneGroup,
    showAll,
    hideAll,
  };
}
