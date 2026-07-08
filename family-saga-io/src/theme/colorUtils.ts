/** Chuyển #rrggbb hoặc rgb(r,g,b) → "H S% L%" cho shadcn */
export function toHslChannels(color: string): string {
  const input = color.trim();
  let r = 0;
  let g = 0;
  let b = 0;

  if (input.startsWith("#")) {
    const h = input.slice(1);
    const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
    r = parseInt(full.slice(0, 2), 16);
    g = parseInt(full.slice(2, 4), 16);
    b = parseInt(full.slice(4, 6), 16);
  } else {
    const m = input.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
    if (!m) return "0 0% 0%";
    r = Number(m[1]);
    g = Number(m[2]);
    b = Number(m[3]);
  }

  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  let hue = 0;
  let sat = 0;
  const lum = (max + min) / 2;

  if (max !== min) {
    const d = max - min;
    sat = lum > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        hue = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        hue = ((b - r) / d + 2) / 6;
        break;
      default:
        hue = ((r - g) / d + 4) / 6;
    }
  }

  return `${Math.round(hue * 360)} ${Math.round(sat * 100)}% ${Math.round(lum * 100)}%`;
}
