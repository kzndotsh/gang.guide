export const MIN_ZOOM = 0.05;
export const MAX_ZOOM = 3;

export function clampZoom(zoom: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom));
}

/** Zoom toward a screen-space focal point while updating pan. */
export function zoomAtPoint(
  zoom: number,
  panX: number,
  panY: number,
  factor: number,
  focalX: number,
  focalY: number
): { zoom: number; panX: number; panY: number } {
  const nextZoom = clampZoom(zoom * factor);
  const ratio = nextZoom / zoom;
  return {
    zoom: nextZoom,
    panX: focalX - (focalX - panX) * ratio,
    panY: focalY - (focalY - panY) * ratio,
  };
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
