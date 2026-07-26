export type GenealogyFlowStepId =
  | "material"
  | "ocr"
  | "extract"
  | "canonical"
  | "visual"
  | "export";

export const GENEALOGY_FLOW_STEPS: GenealogyFlowStepId[] = [
  "material",
  "ocr",
  "extract",
  "canonical",
  "visual",
  "export",
];

export type FlowRouteContext = {
  scanId?: number | string;
  treeId?: string;
};

/** Route mặc định (không có id) — dùng trên Guide / Dashboard khi chưa chọn tài liệu. */
export const GENEALOGY_FLOW_ROUTES: Record<GenealogyFlowStepId, string> = {
  material: "/user/documents/new",
  ocr: "/user/documents?step=ocr",
  extract: "/user/documents/new",
  canonical: "/user/family-trees",
  visual: "/user/family-trees",
  export: "/user/family-trees?tab=export",
};

export function flowRouteForStep(
  stepId: GenealogyFlowStepId,
  ctx: FlowRouteContext = {},
): string {
  const scanId = ctx.scanId != null ? String(ctx.scanId) : null;
  const treeId = ctx.treeId ?? null;

  switch (stepId) {
    case "material":
      return scanId ? `/user/documents/${scanId}` : "/user/documents/new";
    case "ocr":
      return scanId ? `/user/documents/${scanId}?tab=ocr` : "/user/documents?step=ocr";
    case "extract":
      return scanId ? `/user/documents/${scanId}?tab=extract` : "/user/documents/new";
    case "canonical":
      return treeId ? `/user/family-trees/${treeId}?tab=edit` : "/user/family-trees";
    case "visual":
      return treeId ? `/user/family-trees/${treeId}?tab=visual` : "/user/family-trees";
    case "export":
      return treeId ? `/user/family-trees/${treeId}?tab=export` : "/user/family-trees?tab=export";
    default:
      return GENEALOGY_FLOW_ROUTES.material;
  }
}

export function flowTabForStep(stepId: GenealogyFlowStepId): string | null {
  switch (stepId) {
    case "ocr":
      return "ocr";
    case "extract":
      return "extract";
    case "canonical":
      return "edit";
    case "visual":
      return "visual";
    case "export":
      return "export";
    default:
      return null;
  }
}
