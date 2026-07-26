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

export const GENEALOGY_FLOW_ROUTES: Record<GenealogyFlowStepId, string> = {
  material: "/user/documents",
  ocr: "/user/documents",
  extract: "/user/document-reader",
  canonical: "/user/family-trees",
  visual: "/user/family-trees",
  export: "/user/family-trees",
};
