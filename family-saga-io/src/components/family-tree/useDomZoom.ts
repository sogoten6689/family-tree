import { useCallback, useState } from "react";

import { ZOOM_STEP, clampZoom, computeFitScale } from "./familyTreeZoom";

export function useDomZoom(initial = 1) {
  const [scale, setScale] = useState(() => clampZoom(initial));

  const zoomIn = useCallback(() => {
    setScale((prev) => clampZoom(prev + ZOOM_STEP));
  }, []);

  const zoomOut = useCallback(() => {
    setScale((prev) => clampZoom(prev - ZOOM_STEP));
  }, []);

  const setZoom = useCallback((next: number) => {
    setScale(clampZoom(next));
  }, []);

  const reset = useCallback(() => {
    setScale(1);
  }, []);

  const fit = useCallback((container: HTMLElement | null, content: HTMLElement | null) => {
    if (!container || !content) return;
    const next = computeFitScale(
      container.clientWidth,
      container.clientHeight,
      content.scrollWidth,
      content.scrollHeight,
    );
    setScale(next);
  }, []);

  return { scale, zoomIn, zoomOut, setZoom, reset, fit };
}
