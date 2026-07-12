export type RendererId = "dom-classic" | "table" | "cytoscape";

export type RendererMeta = {
  id: RendererId;
  labelKey: string;
  labelDefault: string;
  enabled: boolean;
};

export const VISUAL_SETTINGS_STORAGE_KEY = "ft.visual.v1";

export const FAMILY_TREE_RENDERERS: Record<RendererId, RendererMeta> = {
  "dom-classic": {
    id: "dom-classic",
    labelKey: "familyTree.renderer.domClassic",
    labelDefault: "Cây thẻ",
    enabled: true,
  },
  table: {
    id: "table",
    labelKey: "familyTree.renderer.table",
    labelDefault: "Bảng thành viên",
    enabled: true,
  },
  cytoscape: {
    id: "cytoscape",
    labelKey: "familyTree.renderer.cytoscape",
    labelDefault: "Graph tương tác",
    enabled: false,
  },
};

export const DEFAULT_RENDERER_ID: RendererId = "dom-classic";

export const RENDERER_IDS = Object.keys(FAMILY_TREE_RENDERERS) as RendererId[];

export function isRendererId(value: string): value is RendererId {
  return RENDERER_IDS.includes(value as RendererId);
}

export function loadRendererId(): RendererId {
  try {
    const raw = localStorage.getItem(VISUAL_SETTINGS_STORAGE_KEY);
    if (!raw) return DEFAULT_RENDERER_ID;
    const parsed = JSON.parse(raw) as { rendererId?: string };
    if (parsed.rendererId && isRendererId(parsed.rendererId)) {
      const meta = FAMILY_TREE_RENDERERS[parsed.rendererId];
      return meta.enabled ? parsed.rendererId : DEFAULT_RENDERER_ID;
    }
  } catch {
    // ignore invalid storage
  }
  return DEFAULT_RENDERER_ID;
}

export function saveRendererId(rendererId: RendererId): void {
  localStorage.setItem(VISUAL_SETTINGS_STORAGE_KEY, JSON.stringify({ rendererId }));
}
