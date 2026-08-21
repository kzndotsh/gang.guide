const MIN_ZOOM = 0.05;
const MAX_ZOOM = 3;
const MIN_STAGE_PX = 8;

/** True when the map container has a real layout box (not a 0×0 first paint). */
export function isUsableStageSize(width: number, height: number): boolean {
  return width >= MIN_STAGE_PX && height >= MIN_STAGE_PX;
}

export function clampZoom(zoom: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom));
}

/** Center and scale content to fit inside the viewport. */
export function fitContentInViewport(
  viewportWidth: number,
  viewportHeight: number,
  contentWidth: number,
  contentHeight: number,
  padding = 0.94
): { zoom: number; panX: number; panY: number } {
  if (!viewportWidth || !contentWidth) {
    return { zoom: 1, panX: 0, panY: 0 };
  }
  const zoom = Math.min(viewportWidth / contentWidth, viewportHeight / contentHeight, 1) * padding;
  return {
    zoom,
    panX: (viewportWidth - contentWidth * zoom) / 2,
    panY: (viewportHeight - contentHeight * zoom) / 2,
  };
}
