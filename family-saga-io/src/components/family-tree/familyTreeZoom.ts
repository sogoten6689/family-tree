export const MIN_ZOOM = 0.25;
export const MAX_ZOOM = 2;
export const ZOOM_STEP = 0.1;
export const ZOOM_PRESETS = [0.5, 0.75, 1, 1.25, 1.5] as const;

export function clampZoom(value: number): number {
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value));
}

export function zoomToPercent(scale: number): number {
  return Math.round(scale * 100);
}

export function percentToZoom(percent: number): number {
  return clampZoom(percent / 100);
}

export function computeFitScale(
  containerWidth: number,
  containerHeight: number,
  contentWidth: number,
  contentHeight: number,
): number {
  if (contentWidth <= 0 || contentHeight <= 0) return 1;
  const scale = Math.min(containerWidth / contentWidth, containerHeight / contentHeight) * 0.95;
  return clampZoom(scale);
}
