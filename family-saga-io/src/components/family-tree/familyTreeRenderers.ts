export type RendererId = "dom-classic" | "table" | "cytoscape-dagre" | "print-preview";

export type ThemeId = "default" | "minimal";

export type RendererMeta = {
  id: RendererId;
  labelKey: string;
  labelDefault: string;
  enabled: boolean;
  group: "dom" | "table" | "graph" | "print";
};

export type ThemeMeta = {
  id: ThemeId;
  labelKey: string;
  labelDefault: string;
};

export type FamilyTreeVisualSettings = {
  rendererId: RendererId;
  themeId: ThemeId;
};

export const VISUAL_SETTINGS_STORAGE_KEY = "ft.visual.v1";

export const FAMILY_TREE_RENDERERS: Record<RendererId, RendererMeta> = {
  "dom-classic": {
    id: "dom-classic",
    labelKey: "familyTree.renderer.domClassic",
    labelDefault: "Cây thẻ",
    enabled: true,
    group: "dom",
  },
  table: {
    id: "table",
    labelKey: "familyTree.renderer.table",
    labelDefault: "Bảng thành viên",
    enabled: true,
    group: "table",
  },
  "cytoscape-dagre": {
    id: "cytoscape-dagre",
    labelKey: "familyTree.renderer.cytoscape",
    labelDefault: "Graph tương tác",
    enabled: true,
    group: "graph",
  },
  "print-preview": {
    id: "print-preview",
    labelKey: "familyTree.renderer.printPreview",
    labelDefault: "Xem trước in",
    enabled: true,
    group: "print",
  },
};

export const FAMILY_TREE_THEMES: Record<ThemeId, ThemeMeta> = {
  default: {
    id: "default",
    labelKey: "familyTree.renderer.themeDefault",
    labelDefault: "Mặc định",
  },
  minimal: {
    id: "minimal",
    labelKey: "familyTree.renderer.themeMinimal",
    labelDefault: "Tối giản",
  },
};

export const DEFAULT_RENDERER_ID: RendererId = "dom-classic";
export const DEFAULT_THEME_ID: ThemeId = "default";

export const RENDERER_IDS = Object.keys(FAMILY_TREE_RENDERERS) as RendererId[];
export const THEME_IDS = Object.keys(FAMILY_TREE_THEMES) as ThemeId[];

const DOM_RENDERERS: RendererId[] = ["dom-classic"];

export function isRendererId(value: string): value is RendererId {
  return RENDERER_IDS.includes(value as RendererId);
}

export function isThemeId(value: string): value is ThemeId {
  return THEME_IDS.includes(value as ThemeId);
}

export function supportsTheme(rendererId: RendererId): boolean {
  return DOM_RENDERERS.includes(rendererId);
}

export function supportsFullScreen(rendererId: RendererId): boolean {
  return rendererId !== "print-preview";
}

function parseRendererFromUrl(): RendererId | null {
  if (typeof window === "undefined") return null;
  const raw = new URLSearchParams(window.location.search).get("renderer");
  const value = raw === "cytoscape" ? "cytoscape-dagre" : raw;
  if (value && isRendererId(value) && FAMILY_TREE_RENDERERS[value].enabled) {
    return value;
  }
  return null;
}

export function loadVisualSettings(): FamilyTreeVisualSettings {
  const fromUrl = parseRendererFromUrl();
  try {
    const raw = localStorage.getItem(VISUAL_SETTINGS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<FamilyTreeVisualSettings> & { rendererId?: string };
      const storedRenderer =
        parsed.rendererId === "cytoscape" ? "cytoscape-dagre" : parsed.rendererId;
      const rendererId =
        fromUrl ??
        (storedRenderer && isRendererId(storedRenderer) && FAMILY_TREE_RENDERERS[storedRenderer].enabled
          ? storedRenderer
          : DEFAULT_RENDERER_ID);
      const themeId =
        parsed.themeId && isThemeId(parsed.themeId) ? parsed.themeId : DEFAULT_THEME_ID;
      return { rendererId, themeId };
    }
  } catch {
    // ignore invalid storage
  }
  return {
    rendererId: fromUrl ?? DEFAULT_RENDERER_ID,
    themeId: DEFAULT_THEME_ID,
  };
}

export function saveVisualSettings(settings: FamilyTreeVisualSettings): void {
  localStorage.setItem(VISUAL_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
}

/** @deprecated use loadVisualSettings */
export function loadRendererId(): RendererId {
  return loadVisualSettings().rendererId;
}

/** @deprecated use saveVisualSettings */
export function saveRendererId(rendererId: RendererId): void {
  saveVisualSettings({ ...loadVisualSettings(), rendererId });
}
